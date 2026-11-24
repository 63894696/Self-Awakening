import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from self_awaken.answer_cache import AnswerCache, cache_key, default_cache_path
from self_awaken.capability import check_capability
from self_awaken.schemas import Probe


def make_probe(probe_id: str, category: str = "code", expected: str = "A") -> Probe:
    return Probe(id=probe_id, category=category, prompt=f"question {probe_id}?", expected=expected)


class FakeCompletion:
    def __init__(self, answer, finish_reason="stop", prompt_tokens=20, completion_tokens=5):
        self.answer = answer
        self.latency_ms = 10
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.raw_model = "test-model"
        self.finish_reason = finish_reason


class CacheKeyTests(unittest.TestCase):
    def test_same_request_same_key(self):
        a = cache_key(endpoint="https://x/v1", model="m", prompt="p", temperature=0.0)
        b = cache_key(endpoint="https://x/v1/", model="m", prompt="p", temperature=0.0)
        self.assertEqual(a, b)

    def test_different_model_different_key(self):
        a = cache_key(endpoint="https://x/v1", model="model-a", prompt="p", temperature=0.0)
        b = cache_key(endpoint="https://x/v1", model="model-b", prompt="p", temperature=0.0)
        self.assertNotEqual(a, b)

    def test_different_endpoint_different_key(self):
        a = cache_key(endpoint="https://a/v1", model="m", prompt="p", temperature=0.0)
        b = cache_key(endpoint="https://b/v1", model="m", prompt="p", temperature=0.0)
        self.assertNotEqual(a, b)

    def test_different_temperature_different_key(self):
        a = cache_key(endpoint="https://x/v1", model="m", prompt="p", temperature=0.0)
        b = cache_key(endpoint="https://x/v1", model="m", prompt="p", temperature=0.7)
        self.assertNotEqual(a, b)

    def test_default_path_is_outside_cwd(self):
        path = default_cache_path()
        self.assertNotEqual(path.parent.name, "")
        self.assertIn("self-awaken", str(path))


class AnswerCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "cache.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_put_then_get_roundtrip(self):
        cache = AnswerCache(self.path)
        key = cache_key(endpoint="https://x/v1", model="m", prompt="p", temperature=0.0)
        cache.put(key, FakeCompletion("hello"))

        reopened = AnswerCache(self.path)
        hit = reopened.get(key)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.answer, "hello")

    def test_truncated_answer_is_not_cached(self):
        cache = AnswerCache(self.path)
        key = "k"
        cache.put(key, FakeCompletion("'", finish_reason="length"))
        self.assertIsNone(cache.get(key))

    def test_empty_answer_is_not_cached(self):
        cache = AnswerCache(self.path)
        cache.put("k", FakeCompletion("   "))
        self.assertIsNone(cache.get("k"))

    def test_corrupt_line_is_ignored(self):
        self.path.write_text('{"key": "a", "value": {"answer": "x"}}\nnot json\n', encoding="utf-8")
        cache = AnswerCache(self.path)
        self.assertEqual(len(cache), 1)

    def test_disabled_cache_never_hits(self):
        cache = AnswerCache(self.path, enabled=False)
        cache.put("k", FakeCompletion("a"))
        self.assertIsNone(cache.get("k"))
        self.assertFalse(self.path.exists())


class CachedCapabilityRunTests(unittest.TestCase):
    def test_second_run_makes_no_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.jsonl"
            probes = [make_probe(f"code-{i}") for i in range(12)]
            calls = {"n": 0}

            def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
                calls["n"] += 1
                return FakeCompletion("A")

            with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
                first = check_capability(
                    endpoint="https://example.invalid/v1",
                    api_key="test",
                    model="test-model",
                    probes=probes,
                    profile="code",
                    pack="smoke",
                    max_tokens=160,
                    cache=AnswerCache(cache_path),
                )
                first_calls = calls["n"]
                second = check_capability(
                    endpoint="https://example.invalid/v1",
                    api_key="test",
                    model="test-model",
                    probes=probes,
                    profile="code",
                    pack="smoke",
                    max_tokens=160,
                    cache=AnswerCache(cache_path),
                )

        self.assertEqual(first["verdict"], "sufficient")
        self.assertEqual(second["verdict"], "sufficient")
        self.assertEqual(calls["n"], first_calls, "cached run must not call the API again")
        self.assertEqual(second["cache_hits"], second["probes_run"])
        self.assertEqual(second["used_tokens"], 0)
        self.assertGreater(first["used_tokens"], 0)

    def test_cache_does_not_leak_across_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.jsonl"
            probes = [make_probe(f"code-{i}") for i in range(12)]
            calls = {"n": 0}

            def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
                calls["n"] += 1
                return FakeCompletion("A")

            with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
                check_capability(
                    endpoint="https://example.invalid/v1", api_key="t", model="model-a",
                    probes=probes, profile="code", pack="smoke", max_tokens=160,
                    cache=AnswerCache(cache_path),
                )
                before = calls["n"]
                check_capability(
                    endpoint="https://example.invalid/v1", api_key="t", model="model-b",
                    probes=probes, profile="code", pack="smoke", max_tokens=160,
                    cache=AnswerCache(cache_path),
                )

        self.assertGreater(calls["n"], before, "a different model must not reuse another model's answers")


if __name__ == "__main__":
    unittest.main()

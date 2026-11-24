import unittest
from unittest.mock import patch

from self_awaken.capability import (
    PROFILES,
    check_capability,
    estimate_tokens,
    judge,
    select_probes,
    wilson_interval,
)
from self_awaken.schemas import Probe


def make_probe(probe_id: str, category: str, expected: str = "A") -> Probe:
    return Probe(id=probe_id, category=category, prompt=f"question {probe_id}?", expected=expected)


class WilsonIntervalTests(unittest.TestCase):
    def test_wide_interval_for_small_samples(self):
        low, high = wilson_interval(8, 8)
        self.assertLess(low, 0.8)
        self.assertGreater(high, 0.95)

    def test_narrow_interval_for_large_samples(self):
        low, high = wilson_interval(80, 100)
        self.assertGreater(low, 0.7)
        self.assertLess(high, 0.9)

    def test_empty_sample_is_uninformative(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))


class JudgeTests(unittest.TestCase):
    def test_needs_minimum_probes(self):
        verdict = judge(6, 6, threshold=0.8, min_probes=10)
        self.assertEqual(verdict.verdict, "undetermined")
        self.assertEqual(verdict.reason, "need_more_probes")

    def test_all_correct_above_threshold_is_sufficient(self):
        verdict = judge(20, 20, threshold=0.8, min_probes=10)
        self.assertEqual(verdict.verdict, "sufficient")

    def test_bad_run_is_insufficient(self):
        verdict = judge(4, 20, threshold=0.8, min_probes=10)
        self.assertEqual(verdict.verdict, "insufficient")

    def test_middle_run_stays_undetermined(self):
        verdict = judge(8, 10, threshold=0.8, min_probes=10)
        self.assertEqual(verdict.verdict, "undetermined")


class ProbeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.probes = [
            make_probe("code-1", "code"),
            make_probe("code-2", "code"),
            make_probe("logic-1", "logic"),
            make_probe("logic-2", "logic"),
        ]

    def test_profile_filters_categories(self):
        selected = select_probes(self.probes, "code", "smoke")
        self.assertTrue(selected)
        self.assertTrue(all(probe.category == "code" for probe in selected))

    def test_round_robin_covers_categories(self):
        selected = select_probes(self.probes, "reasoning", "smoke")
        categories = {probe.category for probe in selected}
        self.assertEqual(categories, {"logic"})

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError):
            select_probes(self.probes, "no-such-profile", "smoke")

    def test_pack_size_limits_output(self):
        many = [make_probe(f"code-{i}", "code") for i in range(40)]
        self.assertEqual(len(select_probes(many, "code", "smoke")), 12)


class EstimateTests(unittest.TestCase):
    def test_estimate_counts_prompt_and_output(self):
        probes = [make_probe("a", "code"), make_probe("b", "code")]
        self.assertGreater(estimate_tokens(probes, 100), 200)


class CheckCapabilityTests(unittest.TestCase):
    def test_early_stops_once_sufficient(self):
        probes = [make_probe(f"code-{i}", "code") for i in range(30)]
        calls = {"n": 0}

        def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
            calls["n"] += 1
            return FakeCompletion("A")

        with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
            report = check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=probes,
                profile="code",
                pack="deep",
                min_probes=10,
            )

        self.assertEqual(report["verdict"], "sufficient")
        self.assertLess(calls["n"], len(probes))
        self.assertEqual(report["scored"], calls["n"])

    def test_token_budget_stops_early(self):
        probes = [make_probe(f"code-{i}", "code") for i in range(30)]
        calls = {"n": 0}

        def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
            calls["n"] += 1
            # Flip between right and wrong so the interval never resolves.
            return FakeCompletion("A" if calls["n"] % 2 else "B", prompt_tokens=400, completion_tokens=100)

        with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
            report = check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=probes,
                profile="code",
                pack="deep",
                token_budget=1000,
                min_probes=3,
            )

        self.assertEqual(report["verdict"], "undetermined")
        self.assertEqual(report["reason"], "token_budget_exhausted")
        self.assertLess(report["probes_run"], len(probes))

    def test_errors_do_not_count_as_passes(self):
        probes = [make_probe(f"code-{i}", "code") for i in range(12)]

        def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
            raise RuntimeError("boom")

        with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
            report = check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=probes,
                profile="code",
                pack="smoke",
                min_probes=3,
            )

        self.assertEqual(report["verdict"], "undetermined")
        self.assertEqual(report["scored"], 0)

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError):
            check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=[make_probe("code-1", "code")],
                profile="nope",
            )

    def test_truncated_answer_is_retried_with_larger_budget(self):
        probes = [make_probe(f"code-{i}", "code") for i in range(12)]
        calls = {"n": 0, "max_tokens": []}

        def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
            calls["n"] += 1
            calls["max_tokens"].append(max_tokens)
            if calls["n"] == 1:
                return FakeCompletion("'", finish_reason="length")
            return FakeCompletion("A")

        with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
            report = check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=probes,
                profile="code",
                pack="smoke",
                max_tokens=160,
                min_probes=5,
            )

        self.assertGreater(max(calls["max_tokens"]), 160)
        self.assertEqual(report["scored"], report["probes_run"])
        self.assertEqual(report["results"][0]["error"], None)

    def test_unrecoverable_truncation_is_not_scored_as_wrong(self):
        probes = [make_probe(f"code-{i}", "code") for i in range(12)]

        def fake_complete(self, prompt, temperature=0.0, max_tokens=192):
            return FakeCompletion("'", finish_reason="length")

        with patch("self_awaken.client.OpenAICompatibleClient.complete", fake_complete):
            report = check_capability(
                endpoint="https://example.invalid/v1",
                api_key="test",
                model="test-model",
                probes=probes,
                profile="code",
                pack="smoke",
                max_tokens=512,
                min_probes=5,
            )

        self.assertEqual(report["results"][0]["error"], "truncated_output")
        self.assertIsNone(report["results"][0]["score"])

    def test_all_profiles_have_usable_thresholds(self):
        for name, spec in PROFILES.items():
            self.assertTrue(spec["categories"], name)
            self.assertGreater(spec["threshold"], 0.5, name)
            self.assertLessEqual(spec["threshold"], 1.0, name)


class FakeCompletion:
    def __init__(
        self,
        answer,
        latency_ms=10,
        prompt_tokens=20,
        completion_tokens=5,
        finish_reason="stop",
    ):
        self.answer = answer
        self.latency_ms = latency_ms
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.raw_model = "test-model"
        self.finish_reason = finish_reason


if __name__ == "__main__":
    unittest.main()

import unittest

from self_awaken.fingerprint import compare_run_to_baselines, make_baseline, summarize_results


class FingerprintTests(unittest.TestCase):
    def test_summarize_results(self):
        summary = summarize_results(
            [
                {"score": 1.0, "latency_ms": 100, "completion_tokens": 2},
                {"score": 0.0, "latency_ms": 200, "completion_tokens": 4},
            ]
        )
        self.assertEqual(summary["probe_count"], 2)
        self.assertEqual(summary["accuracy"], 0.5)
        self.assertEqual(summary["avg_latency_ms"], 150)

    def test_compare_identical_run_and_baseline(self):
        run = {
            "requested_model": "demo",
            "endpoint": "local",
            "temperature": 0,
            "max_tokens": 16,
            "summary": {"probe_count": 5, "scored_count": 5, "accuracy": 1.0},
            "results": [
                {
                    "probe_id": f"p{i}",
                    "category": "logic",
                    "prompt": "x",
                    "answer": "B",
                    "expected": "B",
                    "score": 1.0,
                    "choice": "B",
                    "latency_ms": 10,
                }
                for i in range(5)
            ],
        }
        baseline = make_baseline(run, "demo baseline")
        comparison = compare_run_to_baselines(run, [baseline])
        top = comparison["comparisons"][0]
        self.assertEqual(top["similarity"], 1.0)
        self.assertEqual(top["confidence"], "high")


if __name__ == "__main__":
    unittest.main()


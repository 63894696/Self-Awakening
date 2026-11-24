import unittest
import json
from self_awaken.probe_loader import load_probes
from self_awaken.models import Probe

class TestProbeLoader(unittest.TestCase):
    def test_load_single_probe(self):
        # Use a small temporary probe file with one record
        sample_json = '{"id":"math-001","category":"math","prompt":"7 * 23 - 19 = ?","expected":"372","tags":["objective","arithmetic"]}'
        with open("tmp_sample.jsonl", "w", encoding="utf-8") as f:
            f.write(sample_json + "\n")
        
        probes = list(load_probes("tmp_sample.jsonl"))
        self.assertEqual(len(probes), 1)
        probe: Probe = probes[0]
        self.assertEqual(probe.id, "math-001")
        self.assertEqual(probe.category, "math")
        self.assertEqual(probe.prompt, "7 * 23 - 19 = ?")
        self.assertEqual(probe.expected, "372")
        self.assertEqual(probe.tags, ["objective", "arithmetic"])
        # Clean up
        import os
        os.remove("tmp_sample.jsonl")

    def test_load_multiple_probes(self):
        # Load the existing core.zh.jsonl (already verified to exist)
        probes = list(load_probes("data/probes/core.zh.jsonl"))
        self.assertGreaterEqual(len(probes), 3)  # At least 3 probes loaded
        # Validate structure of first probe
        first: Probe = probes[0]
        self.assertIn(first.id, ["math-001", "logic-001", "code-001", "instruction-001", "knowledge-001", "ambiguity-001"])
        self.assertIn(first.category, ["math", "logic", "code", "instruction", "knowledge", "reasoning"])
        self.assertIsInstance(first.prompt, str)
        self.assertIsInstance(first.expected, str)
        self.assertIsInstance(first.tags, list)

if __name__ == "__main__":
    unittest.main()

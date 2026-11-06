import unittest
from core.prompts import build_chunk_prompt, build_summary_prompt

class TestPrompts(unittest.TestCase):
    def test_chunk_prompt_contains_mandatory_schema_rules(self):
        prompt = build_chunk_prompt('Line 5: IP=203.0.113.44', 0, 1, "previous findings context")
        # Check required fields
        self.assertIn('"type":', prompt)
        self.assertIn('"severity":"Low|Medium|High|Critical"', prompt)
        self.assertIn('"lines":', prompt)
        self.assertIn('"evidence":', prompt)
        self.assertIn('"reason":', prompt)
        self.assertIn('"action":', prompt)
        # Check context
        self.assertIn("previous findings context", prompt)
        self.assertTrue(prompt.endswith("###"))

    def test_summary_prompt_structure(self):
        findings = '{"type":"brute_force","ip":"203.0.113.44","lines":[5,13]}'
        summary_prompt = build_summary_prompt(findings)
        self.assertIn("attack_chains", summary_prompt)
        self.assertIn("top_malicious_ips", summary_prompt)
        self.assertIn("recommendations", summary_prompt)
        self.assertTrue(summary_prompt.endswith("###"))

if __name__ == "__main__":
    unittest.main()

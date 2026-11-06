import unittest
from core.analyzer import parse_findings_from_text, merge_findings, build_fallback_report

class TestAnalyzerMerge(unittest.TestCase):
    def test_parse_findings_from_text(self):
        raw = (
            'Some random prose from model\n'
            '{"type":"sql_injection","severity":"High","ip":"203.0.113.72","lines":[29],"evidence":"UNION SELECT","reason":"sqli test","action":"block"}\n'
            '{"type":"clean","severity":"None","ip":"","lines":[],"evidence":"ok","reason":"","action":"none"}\n'
        )
        findings = parse_findings_from_text(raw)
        # Real attacks returned; clean/none correctly filtered out
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "sql_injection")
        self.assertEqual(findings[0]["lines"], [29])

    def test_merge_findings_handles_string_and_mixed_lines(self):
        findings = [
            {"type": "sql_injection", "severity": "Medium", "ip": "1.1.1.1", "lines": "29", "chunk": 1},
            {"type": "sql_injection", "severity": "High", "ip": "1.1.1.1", "lines": [30, "31"], "chunk": 2},
        ]
        merged = merge_findings(findings)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["lines"], [29, 30, 31])

    def test_merge_findings_across_chunks(self):
        chunk1_findings = [
            {"type": "brute_force", "severity": "Medium", "ip": "203.0.113.44", "lines": [5, 13], "chunk": 1}
        ]
        chunk2_findings = [
            {"type": "brute_force", "severity": "High", "ip": "203.0.113.44", "lines": [23, 35], "chunk": 2}
        ]
        all_findings = chunk1_findings + chunk2_findings
        merged = merge_findings(all_findings)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["ip"], "203.0.113.44")
        self.assertEqual(merged[0]["lines"], [5, 13, 23, 35])
        self.assertEqual(merged[0]["severity"], "High")  # upgraded severity
        self.assertEqual(merged[0]["chunks"], [1, 2])

    def test_build_fallback_report(self):
        findings = [
            {"type": "sql_injection", "severity": "High", "ip": "1.2.3.4", "lines": [10], "evidence": "quote", "reason": "why", "action": "block"}
        ]
        report = build_fallback_report(findings, "raw text")
        self.assertEqual(report["total_threats"], 1)
        self.assertEqual(len(report["attack_chains"]), 1)
        self.assertEqual(report["attack_chains"][0]["actors"], ["1.2.3.4"])
        self.assertIn("1.2.3.4", report["top_malicious_ips"])

if __name__ == "__main__":
    unittest.main()

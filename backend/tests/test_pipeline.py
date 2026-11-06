import unittest
from unittest.mock import patch
from core.analyzer import analyze_job

class TestPipeline(unittest.TestCase):
    @patch("core.analyzer.call_model")
    def test_analyze_job_full_flow(self, mock_call):
        mock_call.side_effect = [
            '[{"type":"brute_force","severity":"High","ip":"203.0.113.44","lines":[5],"evidence":"failed","reason":"test","action":"ban"}]',
            '{"summary":"Detected incident","total_threats":1}'
        ]
        sample_log = '{"time":"2026-11-01T08:00:00Z","client_ip":"203.0.113.44","path":"/login","status":401}\n'
        jobs = {"job1": {}}

        analyze_job("job1", sample_log, jobs)

        self.assertEqual(jobs["job1"]["status"], "done")
        self.assertEqual(jobs["job1"]["progress"], 100)
        self.assertEqual(len(jobs["job1"]["chunk_findings"]), 1)
        self.assertTrue(jobs["job1"]["report"]["summary"])
        self.assertEqual(jobs["job1"]["report"]["total_threats"], 1)

if __name__ == "__main__":
    unittest.main()

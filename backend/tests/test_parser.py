import unittest
from core.parser import parse_log_file, chunk_entries, entries_to_text

class TestParser(unittest.TestCase):
    def setUp(self):
        self.sample_logs = (
            '{"time":"2026-11-01T08:00:00Z","client_ip":"192.168.1.1","path":"/login","status":200}\n'
            'invalid non-json line here\n'
            '{"time":"2026-11-01T08:01:00Z","client_ip":"10.0.0.1","path":"/api/data","status":404}\n'
        )

    def test_parse_log_file_with_line_numbers(self):
        entries = parse_log_file(self.sample_logs)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["_line"], 1)
        self.assertEqual(entries[0]["client_ip"], "192.168.1.1")
        self.assertEqual(entries[1]["_line"], 2)
        self.assertEqual(entries[1]["_raw"], "invalid non-json line here")
        self.assertEqual(entries[2]["_line"], 3)
        self.assertEqual(entries[2]["status"], 404)

    def test_chunking_logic(self):
        entries = [{"_line": i, "data": f"item_{i}"} for i in range(1, 75)]
        chunks = chunk_entries(entries, chunk_size=30)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 30)
        self.assertEqual(len(chunks[1]), 30)
        self.assertEqual(len(chunks[2]), 14)
        self.assertEqual(chunks[0][0]["_line"], 1)
        self.assertEqual(chunks[1][0]["_line"], 31)

    def test_entries_to_text(self):
        entries = [{"_line": 1, "client_ip": "1.2.3.4", "method": "GET", "path": "/api"}]
        text = entries_to_text(entries)
        self.assertIn("Line 1: IP=1.2.3.4", text)
        self.assertIn("GET /api", text)

if __name__ == "__main__":
    unittest.main()

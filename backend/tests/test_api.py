import unittest
import io
from unittest.mock import patch
from app import app
from api import routes

class TestAPI(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    @patch("api.routes.check_ollama")
    def test_health_endpoint(self, mock_check):
        mock_check.return_value = (True, "qwen3.5:0.8b")
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["ollama"])

    def test_analyze_empty_request(self):
        resp = self.client.post("/api/analyze")
        self.assertEqual(resp.status_code, 400)

    @patch("api.routes.threading.Thread")
    def test_analyze_valid_file(self, mock_thread):
        data = {"file": (io.BytesIO(b'{"time":"t","path":"/"}\n'), "test.log")}
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res = resp.get_json()
        self.assertIn("job_id", res)
        self.assertEqual(res["status"], "queued")

    def test_status_and_report_not_found(self):
        resp = self.client.get("/api/status/invalid_id")
        self.assertEqual(resp.status_code, 404)
        resp2 = self.client.get("/api/report/invalid_id")
        self.assertEqual(resp2.status_code, 404)

if __name__ == "__main__":
    unittest.main()


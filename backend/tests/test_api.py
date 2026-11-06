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
        # Clear jobs for clean state
        routes.jobs.clear()
        data = {"file": (io.BytesIO(b'{"time":"t","path":"/"}\n'), "test.log")}
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res = resp.get_json()
        self.assertIn("job_id", res)
        self.assertEqual(res["status"], "queued")

    def test_analyze_rejects_concurrent_upload_when_active(self):
        # Simulate an already running analysis
        routes.jobs["active1"] = {
            "job_id": "active1",
            "status": "analyzing"
        }
        data = {"file": (io.BytesIO(b'{"time":"t","path":"/"}\n'), "second.log")}
        resp = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 409)
        d = resp.get_json()
        self.assertIn("already running", d["error"])
        routes.jobs.clear()

    def test_cancel_and_discard_endpoints(self):
        routes.jobs["job_to_cancel"] = {
            "job_id": "job_to_cancel",
            "status": "analyzing"
        }
        # Cancel
        c_resp = self.client.post("/api/cancel/job_to_cancel")
        self.assertEqual(c_resp.status_code, 200)
        self.assertEqual(c_resp.get_json()["status"], "cancelled")

        # Discard
        d_resp = self.client.post("/api/discard/job_to_cancel")
        self.assertEqual(d_resp.status_code, 200)
        self.assertEqual(d_resp.get_json()["status"], "discarded")
        self.assertNotIn("job_to_cancel", routes.jobs)

    def test_active_session_endpoint(self):
        routes.jobs.clear()
        resp = self.client.get("/api/active-session")
        self.assertFalse(resp.get_json()["has_active"])

        routes.jobs["running_j"] = {
            "job_id": "running_j",
            "status": "analyzing",
            "filename": "server.log",
            "current_chunk": 2,
            "total_chunks": 9
        }
        resp2 = self.client.get("/api/active-session")
        d2 = resp2.get_json()
        self.assertTrue(d2["has_active"])
        self.assertEqual(d2["job_id"], "running_j")
        routes.jobs.clear()

    def test_status_and_report_not_found(self):
        resp = self.client.get("/api/status/invalid_id")
        self.assertEqual(resp.status_code, 404)
        resp2 = self.client.get("/api/report/invalid_id")
        self.assertEqual(resp2.status_code, 404)

if __name__ == "__main__":
    unittest.main()


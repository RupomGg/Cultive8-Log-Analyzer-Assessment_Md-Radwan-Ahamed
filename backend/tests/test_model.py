import unittest
from unittest.mock import patch, MagicMock
from core import model
import config

class TestModel(unittest.TestCase):
    @patch("requests.get")
    def test_check_ollama_online(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "qwen3.5:0.8b"}]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ok, msg = model.check_ollama()
        self.assertTrue(ok)
        self.assertIn("qwen3.5:0.8b", msg)

    @patch("requests.get")
    def test_check_ollama_offline(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        ok, msg = model.check_ollama()
        self.assertFalse(ok)
        self.assertIn("Ollama not reachable", msg)

    @patch("requests.post")
    def test_call_model_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": '{"type": "clean"}'}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        res = model.call_model("test prompt")
        self.assertEqual(res, '{"type": "clean"}')

    @patch("requests.post")
    def test_call_model_retry_on_failure(self, mock_post):
        mock_post.side_effect = [Exception("Temporary glitch"), MagicMock(json=lambda: {"response": "recovered"}, raise_for_status=lambda: None)]
        res = model.call_model("retry prompt", retries=1)
        self.assertEqual(res, "recovered")
        self.assertEqual(mock_post.call_count, 2)

    def test_set_model(self):
        original = config.MODEL_NAME
        model.set_model("qwen3.5:2b")
        self.assertEqual(config.MODEL_NAME, "qwen3.5:2b")
        model.set_model(original)

if __name__ == "__main__":
    unittest.main()


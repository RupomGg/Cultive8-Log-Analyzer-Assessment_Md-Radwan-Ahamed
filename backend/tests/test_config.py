import unittest
import os
import config

class TestConfig(unittest.TestCase):
    def test_default_values(self):
        self.assertEqual(config.MAX_TOKENS_PER_CALL, 2048)
        self.assertEqual(config.CHUNK_LINES, 30)
        self.assertIn("qwen", config.MODEL_NAME.lower())
        self.assertTrue(config.UPLOAD_DIR.exists())

    def test_env_override(self):
        original = config.OLLAMA_URL
        os.environ["OLLAMA_URL"] = "http://custom-host:11434"
        import importlib
        importlib.reload(config)
        self.assertEqual(config.OLLAMA_URL, "http://custom-host:11434")
        # cleanup
        os.environ["OLLAMA_URL"] = original
        importlib.reload(config)

if __name__ == "__main__":
    unittest.main()


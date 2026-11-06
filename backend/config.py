import os
from pathlib import Path

# Local inference settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:0.5b")

# Token & chunking constraints
MAX_TOKENS_PER_CALL = 2048
CHUNK_LINES = 30
MODEL_OUTPUT_TOKENS = 512
CONTEXT_FINDINGS = 6

# Upload storage
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

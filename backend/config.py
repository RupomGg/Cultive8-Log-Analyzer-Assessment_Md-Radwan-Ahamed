"""
config.py — Central configuration for the Log Analyzer backend.
All tuneable values live here. Override with environment variables.
"""

import os
from pathlib import Path

# ── Ollama / Model ────────────────────────────────────────────────────────────
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
MODEL_NAME  = os.getenv("MODEL_NAME",  "qwen3.5:0.8b")   # brief-recommended default

# ── Token / chunking limits ───────────────────────────────────────────────────
MAX_TOKENS_PER_CALL = 2048   # hard limit from assessment brief — never exceed this
CHUNK_LINES         = 30     # 30 log lines ≈ 1100 tokens — leaves room for prompt + output
MODEL_OUTPUT_TOKENS = 512    # max tokens the model should produce per call
CONTEXT_FINDINGS    = 6      # how many previous findings to carry into the next chunk

# ── Storage ───────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


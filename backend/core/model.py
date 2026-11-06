import time
import requests
import config


def check_ollama() -> tuple[bool, str]:
    """Check connectivity to Ollama and resolve the active model name."""
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if not models:
            return False, "Ollama is running, but no models are downloaded yet."

        for m in models:
            if m == config.MODEL_NAME or m.startswith(config.MODEL_NAME.split(":")[0]):
                config.MODEL_NAME = m
                return True, m

        # Default to whatever model is locally cached
        config.MODEL_NAME = models[0]
        return True, f"Using installed model: {models[0]}"
    except Exception as e:
        return False, f"Ollama not reachable: {e}"


def call_model(prompt: str, retries: int = 2) -> str:
    """Execute a single inference request with retry backoff."""
    payload = {
        "model": config.MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": config.MODEL_OUTPUT_TOKENS,
            "temperature": 0.1,
            "stop": ["###"]
        }
    }
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                f"{config.OLLAMA_URL}/api/generate",
                json=payload,
                timeout=180
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            if attempt == retries:
                return f"[MODEL_ERROR] {e}"
            time.sleep(2)
    return "[MODEL_ERROR] Max retries exceeded"


def list_models() -> dict:
    """Fetch available models from the local Ollama daemon."""
    r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
    r.raise_for_status()
    return r.json()


def set_model(name: str) -> None:
    """Update target model at runtime."""
    config.MODEL_NAME = name

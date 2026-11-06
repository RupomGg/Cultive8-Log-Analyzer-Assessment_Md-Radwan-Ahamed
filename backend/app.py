import logging
from flask import Flask
from flask_cors import CORS

from api.routes import api, jobs as route_jobs
from core.model import check_ollama
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
CORS(app)

app.register_blueprint(api)

from api import routes
routes.jobs = route_jobs


if __name__ == "__main__":
    logging.info("Starting Log Analyzer backend")
    logging.info("Target model: %s at %s", config.MODEL_NAME, config.OLLAMA_URL)
    logging.info("Constraints: %d lines/chunk, max %d tokens/call", config.CHUNK_LINES, config.MAX_TOKENS_PER_CALL)
    ok, msg = check_ollama()
    logging.info("Ollama status: %s (%s)", "ready" if ok else "not ready", msg)
    app.run(host="0.0.0.0", port=5000, debug=False)

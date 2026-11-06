import uuid
import threading
from flask import Blueprint, request, jsonify

import config
from core.model import check_ollama, list_models, set_model
from core.analyzer import analyze_job, load_checkpoints, get_system_telemetry

api = Blueprint("api", __name__, url_prefix="/api")

# Rehydrate existing jobs from disk to support resume after restart
jobs: dict = load_checkpoints()


@api.route("/health")
def health():
    ok, msg = check_ollama()
    telemetry = get_system_telemetry()
    return jsonify({
        "status": "ok",
        "ollama": ok,
        "model": config.MODEL_NAME,
        "message": msg,
        "telemetry": telemetry
    })


@api.route("/models")
def get_models():
    try:
        return jsonify(list_models())
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@api.route("/set-model", methods=["POST"])
def switch_model():
    data = request.get_json()
    if not data or "model" not in data:
        return jsonify({"error": "model field required"}), 400
    set_model(data["model"])
    return jsonify({"model": config.MODEL_NAME, "message": f"Switched to {config.MODEL_NAME}"})


@api.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    content = f.read().decode("utf-8", errors="replace")
    if not content.strip():
        return jsonify({"error": "File is empty"}), 400

    line_count = content.count("\n") + 1
    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "job_id": job_id,
        "filename": f.filename,
        "line_count": line_count,
        "status": "queued",
        "progress": 0,
        "current_chunk": 0,
        "total_chunks": 0,
        "chunk_findings": [],
        "all_findings": [],
        "report": None,
        "error": None
    }

    save_path = config.UPLOAD_DIR / f"{job_id}_{f.filename}"
    save_path.write_text(content, encoding="utf-8")

    thread = threading.Thread(
        target=analyze_job,
        args=(job_id, content, jobs),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id, "line_count": line_count, "status": "queued"})


@api.route("/resume/<job_id>", methods=["POST"])
def resume_job(job_id):
    """Resume an interrupted or paused job from its last checkpoint."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]

    if job.get("status") == "done":
        return jsonify({"message": "Job is already completed", "status": "done"}), 200

    # Locate uploaded source file
    saved_files = list(config.UPLOAD_DIR.glob(f"{job_id}_*"))
    if not saved_files:
        return jsonify({"error": "Original log file not found on disk"}), 404

    content = saved_files[0].read_text(encoding="utf-8", errors="replace")
    thread = threading.Thread(
        target=analyze_job,
        args=(job_id, content, jobs),
        daemon=True
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "resumed_from_chunk": job.get("current_chunk", 0),
        "status": "resumed"
    })


@api.route("/status/<job_id>")
def status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    telemetry = get_system_telemetry()
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "current_chunk": job.get("current_chunk", 0),
        "total_chunks": job.get("total_chunks", 0),
        "filename": job.get("filename"),
        "line_count": job.get("line_count"),
        "model_calls_made": job.get("model_calls_made", 0),
        "model_calls_saved": job.get("model_calls_saved", 0),
        "total_inference_time_s": job.get("total_inference_time", 0.0),
        "telemetry": telemetry,
        "error": job.get("error")
    })


@api.route("/report/<job_id>")
def report(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    if job["status"] != "done":
        return jsonify({"error": f"Job not ready. Status: {job['status']}"}), 202
    return jsonify({
        "job_id": job_id,
        "filename": job.get("filename"),
        "report": job["report"],
        "telemetry": job.get("telemetry"),
        "chunk_findings": job["chunk_findings"],
        "total_findings": len([
            f for f in job["all_findings"]
            if f.get("type") not in ("clean", "error")
        ])
    })

import uuid
import threading
from flask import Blueprint, request, jsonify

import config
from core.model import check_ollama, list_models, set_model
from core.analyzer import (
    analyze_job,
    load_checkpoints,
    save_checkpoint,
    delete_checkpoint,
    get_system_telemetry,
)

api = Blueprint("api", __name__, url_prefix="/api")

# Rehydrate existing jobs from disk to support resume after restart
jobs: dict = load_checkpoints()


@api.route("/active-session")
def active_session():
    """Return active or paused session if one exists, ensuring dead sessions don't resurrect."""
    # Find unfinished job in memory
    for jid, j in list(jobs.items()):
        st = j.get("status")
        if st in ("queued", "analyzing", "paused"):
            return jsonify({
                "has_active": True,
                "job_id": jid,
                "status": st,
                "filename": j.get("filename"),
                "current_chunk": j.get("current_chunk", 0),
                "total_chunks": j.get("total_chunks", 0),
                "progress": j.get("progress", 0)
            })

    return jsonify({"has_active": False})


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
    # 1. Enforce single-active-analysis constraint
    active = [j for j in jobs.values() if j.get("status") in ("queued", "analyzing")]
    if active:
        return jsonify({
            "error": "An analysis is already running. Please pause, cancel, or wait for it to finish.",
            "active_job_id": active[0]["job_id"],
            "status": active[0]["status"]
        }), 409

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
        "error": None,
        "cancel_requested": False,
        "pause_requested": False
    }

    save_path = config.UPLOAD_DIR / f"{job_id}_{f.filename}"
    save_path.write_text(content, encoding="utf-8")

    thread = threading.Thread(
        target=analyze_job,
        args=(job_id, content, jobs),
        daemon=True
    )
    thread.start()

    est_chunks = max(1, (line_count + config.CHUNK_LINES - 1) // config.CHUNK_LINES)
    return jsonify({"job_id": job_id, "line_count": line_count, "total_chunks": est_chunks, "status": "queued"})


@api.route("/pause/<job_id>", methods=["POST"])
def pause_job(job_id):
    """Pause an active analysis at the nearest chunk boundary."""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]

    if job.get("status") not in ("queued", "analyzing"):
        return jsonify({"error": f"Cannot pause job with status '{job.get('status')}'"}), 400

    job["pause_requested"] = True
    job["status"] = "paused"
    save_checkpoint(job)
    return jsonify({
        "job_id": job_id,
        "status": "paused",
        "current_chunk": job.get("current_chunk", 0),
        "total_chunks": job.get("total_chunks", 0),
        "message": "Analysis paused."
    })


@api.route("/resume/<job_id>", methods=["POST"])
def resume_job(job_id):
    """Resume an interrupted or paused job from its last checkpoint."""
    if job_id not in jobs:
        # Try loading from disk
        checkpoints = load_checkpoints()
        if job_id in checkpoints:
            jobs[job_id] = checkpoints[job_id]
        else:
            return jsonify({"error": "Job not found"}), 404

    job = jobs[job_id]

    if job.get("status") == "done":
        return jsonify({"message": "Job is already completed", "status": "done"}), 200

    # Ensure no other job is currently active
    active = [j for j in jobs.values() if j.get("job_id") != job_id and j.get("status") in ("queued", "analyzing")]
    if active:
        return jsonify({
            "error": "Another analysis is currently running. Please cancel it before resuming.",
            "active_job_id": active[0]["job_id"]
        }), 409

    job["cancel_requested"] = False
    job["pause_requested"] = False
    job["status"] = "analyzing"

    # Locate uploaded source file (excluding checkpoint JSON)
    saved_files = [
        f for f in config.UPLOAD_DIR.glob(f"{job_id}_*")
        if not f.name.endswith("_checkpoint.json")
    ]
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
        "resumed_from_chunk": len(job.get("chunk_findings", [])),
        "status": "analyzing",
        "message": "Analysis resumed"
    })


@api.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    """Cancel an active or paused job, stopping worker and releasing locks."""
    if job_id not in jobs:
        delete_checkpoint(job_id)
        return jsonify({"job_id": job_id, "status": "cancelled", "message": "Job cancelled"}), 200

    job = jobs[job_id]
    job["cancel_requested"] = True
    job["status"] = "cancelled"
    delete_checkpoint(job_id)
    return jsonify({
        "job_id": job_id,
        "status": "cancelled",
        "message": "Analysis cancelled. File uploads unlocked."
    })


@api.route("/discard/<job_id>", methods=["POST"])
def discard_job(job_id):
    """Completely purge job state from memory and disk."""
    if job_id in jobs:
        job = jobs[job_id]
        job["cancel_requested"] = True
        job["status"] = "discarded"
        del jobs[job_id]
    delete_checkpoint(job_id)
    return jsonify({
        "job_id": job_id,
        "status": "discarded",
        "message": "Session discarded. State completely reset."
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

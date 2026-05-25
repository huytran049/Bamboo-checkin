"""
Face task management: queue, status, Redis/thread dispatch.
Extracted from application.py lines 639-841.
"""
import os
import sys
import json
import time
import uuid
import threading
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app_config import (
    logger, REG_DIR, _FACE_HELPER_PATH,
    _FACE_TASKS, _FACE_TASKS_LOCK, _FACE_TASK_TTL_SEC,
    _FACE_REGISTER_QUEUE, _FACE_RECOGNIZE_QUEUE,
    _FACE_STATUS_PREFIX, _FACE_RECOGNITION_THRESHOLD,
    _HAS_REDIS, redis_client, _USE_REDIS_FACE,
)
from helpers.face_worker_helper import (
    register_face as _register_face_job,
    recognize_face as _recognize_face_job,
)

FACE_JOB_DIR = Path(".runtime") / "face_jobs"
FACE_JOB_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_old_face_tasks() -> None:
    now = time.time()
    with _FACE_TASKS_LOCK:
        expired_ids = [
            task_id
            for task_id, rec in _FACE_TASKS.items()
            if now - float(rec.get("updated_at", rec.get("created_at", 0))) > _FACE_TASK_TTL_SEC
        ]
        for task_id in expired_ids:
            _FACE_TASKS.pop(task_id, None)


def build_face_task_record(
    *,
    task_id: str,
    task_type: str,
    registration_id: str = "",
    image_path: str = "",
):
    now = time.time()
    return {
        "task_id": task_id,
        "type": task_type,
        "status": "queued",
        "registration_id": registration_id,
        "image_path": image_path,
        "matched": False,
        "visitor": None,
        "score": 0.0,
        "quality_score": None,
        "top_matches": [],
        "error": None,
        "created_at": now,
        "updated_at": now,
    }


def set_face_task_status(task_id: str, payload: dict, *, ttl_sec: int = _FACE_TASK_TTL_SEC) -> None:
    payload = {**payload, "task_id": task_id, "updated_at": time.time()}
    with _FACE_TASKS_LOCK:
        _FACE_TASKS[task_id] = payload
    if _HAS_REDIS:
        redis_client.setex(
            f"{_FACE_STATUS_PREFIX}{task_id}",
            ttl_sec,
            json.dumps(payload, ensure_ascii=False),
        )


def get_face_task_status(task_id: str) -> Optional[dict]:
    if _HAS_REDIS:
        raw = redis_client.get(f"{_FACE_STATUS_PREFIX}{task_id}")
        if raw:
            try:
                payload = json.loads(raw)
                with _FACE_TASKS_LOCK:
                    _FACE_TASKS[task_id] = payload
                return payload
            except Exception:
                logger.warning("Failed to parse Redis face status for %s", task_id)
    with _FACE_TASKS_LOCK:
        return _FACE_TASKS.get(task_id)


def save_face_job_image(
    image_bytes: bytes,
    *,
    registration_id: str = "",
    prefix: str = "face_job",
):
    target_dir = FACE_JOB_DIR / registration_id if registration_id else Path(tempfile.gettempdir()) / "bamboo_face_jobs"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"
    image_path = target_dir / filename
    with image_path.open("wb") as fh:
        fh.write(image_bytes)
    return image_path.resolve()


def run_face_helper(task_type: str, image_path: str, registration_id: str = "") -> dict:
    cmd = [
        os.getenv("PYTHON_BIN", "python3"),
        str(_FACE_HELPER_PATH),
        "--type",
        task_type,
        "--image-path",
        str(image_path),
        "--threshold",
        str(_FACE_RECOGNITION_THRESHOLD),
    ]
    if registration_id:
        cmd.extend(["--registration-id", registration_id])
    proc = subprocess.run(
        cmd,
        cwd=str(Path(__file__).resolve().parent.parent),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise RuntimeError((proc.stderr or "Face helper returned no output").strip())
    result = json.loads(stdout)
    if proc.returncode != 0 or not result.get("ok", False):
        raise RuntimeError(result.get("error") or proc.stderr.strip() or "Face helper failed")
    return result


def _process_face_task_inline(task_id: str, task_type: str, image_path: str, registration_id: str = "") -> None:
    status = get_face_task_status(task_id) or build_face_task_record(
        task_id=task_id,
        task_type=task_type,
        registration_id=registration_id,
        image_path=image_path,
    )
    status["status"] = "processing"
    set_face_task_status(task_id, status)
    try:
        if task_type == "register":
            result = _register_face_job(registration_id, image_path)
        elif task_type == "recognize":
            result = _recognize_face_job(image_path, _FACE_RECOGNITION_THRESHOLD)
        else:
            raise ValueError(f"Unsupported face task type: {task_type}")
        status.update(
            {
                "status": "done",
                "matched": bool(result.get("matched")),
                "visitor": result.get("visitor"),
                "score": float(result.get("score", 0.0)),
                "quality_score": result.get("quality_score"),
                "top_matches": result.get("top_matches", []),
                "result": result,
                "error": None,
            }
        )
    except Exception as exc:
        status.update({"status": "error", "error": str(exc)})
    set_face_task_status(task_id, status)


def enqueue_face_task(
    *,
    task_type: str,
    image_bytes: bytes,
    registration_id: str = "",
):
    cleanup_old_face_tasks()
    task_id = f"face_{task_type}_{uuid.uuid4().hex}"
    image_path = save_face_job_image(
        image_bytes,
        registration_id=registration_id,
        prefix=f"{task_type}_input",
    )
    payload = {
        "task_id": task_id,
        "type": task_type,
        "registration_id": registration_id,
        "image_path": str(image_path),
        "python_bin": sys.executable,
        "created_at": time.time(),
        "threshold": _FACE_RECOGNITION_THRESHOLD,
    }
    record = build_face_task_record(
        task_id=task_id,
        task_type=task_type,
        registration_id=registration_id,
        image_path=str(image_path),
    )
    set_face_task_status(task_id, record)
    if _USE_REDIS_FACE:
        queue_name = _FACE_REGISTER_QUEUE if task_type == "register" else _FACE_RECOGNIZE_QUEUE
        redis_client.rpush(queue_name, json.dumps(payload, ensure_ascii=False))
    else:
        thread = threading.Thread(
            target=_process_face_task_inline,
            args=(task_id, task_type, str(image_path), registration_id),
            daemon=True,
        )
        thread.start()
    return task_id, str(image_path)


def schedule_registration_face_embedding(reg_id: str, reg_folder: Path) -> Optional[str]:
    face_path = None
    for ext in ("jpeg", "jpg", "png", "webp"):
        candidate = reg_folder / f"face.{ext}"
        if candidate.exists():
            face_path = candidate
            break
    if face_path is None:
        return None
    try:
        image_bytes = face_path.read_bytes()
        job_id, _ = enqueue_face_task(
            task_type="register",
            image_bytes=image_bytes,
            registration_id=reg_id,
        )
        return job_id
    except Exception as exc:
        logger.warning("Failed to schedule face registration for %s: %s", reg_id, exc)
        return None

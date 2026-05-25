import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import redis

from database.update_database import update_registration_with_ocr
from helpers.registration_sync_helper import update_registration_json_with_ocr


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("kiosk.ocr_redis_worker")

OCR_QUEUE = "ocr_tasks"
OCR_STATUS_PREFIX = "ocr_status:"
OCR_STATUS_TTL_SEC = 3600
SWIFT_BIN = os.getenv("SWIFT_BIN", "swift")
SWIFT_OCR_WORKER = PROJECT_ROOT / "workers_swift" / "ocr_worker.swift"
SWIFT_OCR_TIMEOUT_SEC = float(os.getenv("SWIFT_OCR_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT_SECONDS", "90")))


def get_redis_client() -> redis.Redis:
    client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    client.ping()
    return client


def set_status(client: redis.Redis, task_id: str, payload: dict) -> None:
    rec = {**payload, "updated_at": time.time()}
    client.setex(f"{OCR_STATUS_PREFIX}{task_id}", OCR_STATUS_TTL_SEC, json.dumps(rec, ensure_ascii=False))


def run_swift_ocr(image_path: str) -> dict:
    cmd = [SWIFT_BIN, str(SWIFT_OCR_WORKER), image_path]
    logger.info("Running Swift OCR worker: %s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=SWIFT_OCR_TIMEOUT_SEC,
        check=False,
        env=os.environ.copy(),
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if stderr:
        logger.info("Swift OCR stderr:\n%s", stderr)
    if proc.returncode != 0:
        raise RuntimeError(stderr or stdout or f"Swift OCR failed with code {proc.returncode}")
    if not stdout:
        raise RuntimeError(stderr or "Swift OCR returned empty output")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Swift OCR returned invalid JSON: {exc}: {stdout[:400]}") from exc


def normalize_worker_fields(payload: dict) -> dict:
    return {
        "full_name": str(payload.get("full_name") or payload.get("name") or "").strip(),
        "title": str(payload.get("title") or payload.get("position") or payload.get("role") or "").strip(),
        "email": str(payload.get("email") or "").strip(),
        "company": str(payload.get("company") or payload.get("org") or "").strip(),
        "phone": str(payload.get("phone") or payload.get("tel") or "").strip(),
        "address": str(payload.get("address") or "").strip(),
    }


def process_task(client: redis.Redis, task: dict) -> None:
    task_id = str(task.get("task_id") or "").strip()
    reg_id = str(task.get("reg_id") or "").strip()
    image_path = str(task.get("image_path") or "").strip()
    is_quick = bool(task.get("is_quick"))
    if not task_id or not reg_id or not image_path:
        logger.error("Invalid OCR task payload: %s", task)
        return

    logger.info("Processing OCR task %s reg_id=%s quick=%s", task_id, reg_id, is_quick)
    set_status(
        client,
        task_id,
        {
            "status": "processing",
            "text": "",
            "fields": {},
            "timing": {},
            "error": None,
            "created_at": time.time(),
            "is_quick": is_quick,
            "reg_id": reg_id,
            "bbox": task.get("bbox"),
        },
    )

    t0 = time.time()
    try:
        result = run_swift_ocr(image_path)
        raw_text = str(result.get("raw_ocr") or "").strip()
        worker_error = str(result.get("error") or "").strip()
        fields = normalize_worker_fields(result)

        update_registration_with_ocr(reg_id, fields, raw_text)
        sync_result = update_registration_json_with_ocr(reg_id, fields, raw_text)

        set_status(
            client,
            task_id,
            {
                "status": "done",
                "text": raw_text,
                "fields": fields,
                "timing": {"total": round(time.time() - t0, 3)},
                "error": worker_error or None,
                "reg_id": reg_id,
                "is_quick": is_quick,
                "bbox": task.get("bbox"),
                "sync": sync_result,
            },
        )
        logger.info("Completed OCR task %s reg_id=%s", task_id, reg_id)
    except Exception as exc:
        logger.exception("OCR task failed: %s", task_id)
        set_status(
            client,
            task_id,
            {
                "status": "error",
                "text": "",
                "fields": {},
                "timing": {"total": round(time.time() - t0, 3)},
                "error": str(exc),
                "reg_id": reg_id,
                "is_quick": is_quick,
                "bbox": task.get("bbox"),
            },
        )


def main() -> int:
    client = get_redis_client()
    logger.info("Python OCR Redis worker started. Listening on %s", OCR_QUEUE)
    while True:
        item = client.blpop(OCR_QUEUE, timeout=1)
        if not item:
            continue
        _, raw_payload = item
        try:
            task = json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.error("Failed to parse OCR task JSON: %s", raw_payload)
            continue
        process_task(client, task)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

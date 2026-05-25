"""
OCR processing: sync/async, quick OCR, task queue management.
Extracted from application.py lines 1534-1968.
"""
import json
import time
import uuid
import threading
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from app_config import (
    logger, cv2, _HAS_CV2,
    _ensure_reader, _get_quick_reader,
    _OCR_TASKS, _OCR_TASKS_LOCK, _OCR_TASK_TTL_SEC, _OCR_SEMAPHORE,
    _HAS_REDIS, redis_client, _USE_REDIS_OCR,
)
from card import parse_bcard_with_bbox, parse_bcard_fields
from card.utils import undistort_image
from database.update_database import update_registration_with_ocr
from services.registration import update_registration_json_with_ocr

OCR_RUNTIME_DIR = Path(".runtime") / "ocr_jobs"
OCR_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def run_bcard_ocr_from_image(img: Image.Image, filtering_bbox: dict = None) -> dict:
    """Core OCR pipeline: undistort → OCR → parse fields."""
    ocr_reader = _ensure_reader()
    if ocr_reader is None or getattr(ocr_reader, "engine", None) is None:
        raise RuntimeError("OCR reader is not initialized")
    img = ImageOps.exif_transpose(img).convert("RGB")
    np_img = np.array(img)
    np_img = undistort_image(np_img)
    t_ocr0 = time.time()
    ocr_results = ocr_reader.readtext(np_img, detail=1, paragraph=False)
    t_ocr_done = time.time()

    if isinstance(ocr_results, dict):
        # Result from Swift/Ollama is already parsed fields
        fields = dict(ocr_results)
        text = str(fields.pop("raw_ocr", "") or "").strip()
        worker_error = str(fields.pop("error", "") or "").strip()
        meaningful = any(str(fields.get(k, "") or "").strip() for k in ("full_name", "title", "email", "company", "phone", "address"))

        if text and (worker_error or not meaningful):
            fallback_fields, _ = parse_bcard_fields(text)
            for key in ("full_name", "title", "email", "company", "phone", "address"):
                if not str(fields.get(key, "") or "").strip():
                    fields[key] = fallback_fields.get(key, "")

        if not text:
            text = "\n".join([f"{k}: {v}" for k, v in fields.items() if v]).strip()
    else:
        # Legacy/Fallback: RapidOCR results, needs heuristic parsing
        fields, normalized_ocr = parse_bcard_with_bbox(ocr_results, return_full_results=True, filtering_bbox=filtering_bbox)
        text = "\n".join(t.strip() for (b, t, c, *_) in normalized_ocr if c > 0.3 and t.strip()).strip()

    return {
        "text": text,
        "fields": fields,
        "timing": {
            "ocr": round(t_ocr_done - t_ocr0, 3),
        },
    }


def cleanup_old_ocr_tasks() -> None:
    now = time.time()
    with _OCR_TASKS_LOCK:
        stale_ids = [
            tid for tid, rec in _OCR_TASKS.items()
            if (now - float(rec.get("updated_at", rec.get("created_at", now)))) > _OCR_TASK_TTL_SEC
        ]
        for tid in stale_ids:
            _OCR_TASKS.pop(tid, None)


def get_ocr_task_status(task_id: str) -> Optional[dict]:
    """Retrieve OCR task status from Redis or in-memory store."""
    if _USE_REDIS_OCR:
        redis_payload = redis_client.get(f"ocr_status:{task_id}")
        if redis_payload:
            try:
                rec = json.loads(redis_payload)
                status = str(rec.get("status", "processing")).lower()
                if status == "success":
                    status = "done"
                return {
                    "task_id": task_id,
                    "status": status,
                    "text": rec.get("text", ""),
                    "fields": rec.get("fields", {}),
                    "timing": rec.get("timing", {}),
                    "error": rec.get("error"),
                }
            except Exception:
                logger.exception("Failed to parse Redis OCR status for task_id=%s", task_id)

    with _OCR_TASKS_LOCK:
        rec = _OCR_TASKS.get(task_id)
        if rec is None:
            return None
        status = str(rec.get("status", "processing")).lower()
        if status == "success":
            status = "done"
        return {
            "task_id": task_id,
            "status": status,
            "text": rec.get("text", ""),
            "fields": rec.get("fields", {}),
            "timing": rec.get("timing", {}),
            "error": rec.get("error"),
        }


def _process_ocr_task(task_id: str, image_bytes: bytes) -> None:
    logger.info("Async OCR task started for task_id: %s", task_id)
    t_start = time.time()
    try:
        _OCR_SEMAPHORE.acquire()

        filtering_bbox = None
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec:
                filtering_bbox = rec.get("bbox")

        img = Image.open(BytesIO(image_bytes))
        result = run_bcard_ocr_from_image(img, filtering_bbox=filtering_bbox)
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec is not None:
                rec.update({
                    "status": "done",
                    "text": result["text"],
                    "fields": result["fields"],
                    "timing": {
                        "total": round(time.time() - t_start, 3),
                        "ocr": result["timing"]["ocr"],
                    },
                    "error": None,
                    "updated_at": time.time(),
                })

        # Server-side auto-save: update DB with OCR results
        reg_id = None
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec:
                reg_id = rec.get("reg_id")

        if reg_id:
            logger.info("Auto-save OCR results for reg_id=%s", reg_id)
            update_registration_with_ocr(reg_id, result["fields"], result["text"])
            update_registration_json_with_ocr(reg_id, result["fields"], result["text"])

    except Exception as e:
        logger.exception("Async OCR task failed: %s", task_id)
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec is not None:
                rec.update({
                    "status": "error",
                    "error": str(e),
                    "updated_at": float(time.time()),
                })
    finally:
        _OCR_SEMAPHORE.release()


def _process_quick_ocr_task(task_id: str, image_bytes: bytes) -> None:
    """Quick OCR worker: single pass, regex fields only (3-5s)."""
    t_start = time.time()
    try:
        _OCR_SEMAPHORE.acquire()
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        np_img = np.array(img)
        np_img = undistort_image(np_img)

        h, w = int(np_img.shape[0]), int(np_img.shape[1])
        max_dim = int(max(h, w))
        if max_dim > 640:
            scale = 640.0 / float(max_dim)
            np_img = cv2.resize(np_img, (int(float(w) * scale), int(float(h) * scale)))

        t0 = time.time()
        q_engine = _get_quick_reader()
        if q_engine is None:
            raise ValueError("Quick OCR engine not initialized")

        # Add 30px white padding for edge-text recognition
        np_img_padded = cv2.copyMakeBorder(
            np_img, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )
        raw_result = q_engine(np_img_padded)
        raw_items = raw_result[0] if (raw_result and len(raw_result) > 0 and raw_result[0]) else []

        # Filter by bbox if provided
        filtering_bbox = None
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec:
                filtering_bbox = rec.get("bbox")

        if filtering_bbox and isinstance(filtering_bbox, dict) and raw_items:
            margin = 150
            fx1 = filtering_bbox.get("x1", 0) - margin
            fy1 = filtering_bbox.get("y1", 0) - margin
            fx2 = filtering_bbox.get("x2", 9999) + margin
            fy2 = filtering_bbox.get("y2", 9999) + margin

            filtered = []
            for item in raw_items:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    box = item[0]
                    cx = sum(p[0] for p in box) / 4
                    cy = sum(p[1] for p in box) / 4
                    if fx1 <= cx <= fx2 and fy1 <= cy <= fy2:
                        filtered.append(item)

            if filtered:
                logger.info(f"Quick OCR Filtering: {len(raw_items)} -> {len(filtered)} items kept.")
                raw_items = filtered

        text_parts = []
        for item in raw_items:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                txt = str(item[1]).strip()
                conf = float(item[2])
                if conf > 0.3 and txt:
                    text_parts.append(txt)

        text = "\n".join(text_parts)
        fields, _ = parse_bcard_fields(text)
        t_ocr_done = time.time()

        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec is not None:
                rec.update({
                    "status": "done",
                    "text": text,
                    "fields": fields,
                    "timing": {
                        "total": round(float(time.time() - t_start), 3),
                        "ocr": round(float(t_ocr_done - t0), 3),
                    },
                    "error": None,
                    "updated_at": float(time.time()),
                })

        # Server-side auto-save
        reg_id = None
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec:
                reg_id = rec.get("reg_id")

        if reg_id:
            logger.info("Auto-save Quick OCR results for reg_id=%s", reg_id)
            update_registration_with_ocr(reg_id, fields, text)
            update_registration_json_with_ocr(reg_id, fields, text)

    except Exception as e:
        logger.exception("Async QUICK OCR task failed: %s", task_id)
        with _OCR_TASKS_LOCK:
            rec = _OCR_TASKS.get(task_id)
            if rec is not None:
                rec.update({
                    "status": "error",
                    "error": str(e),
                    "updated_at": time.time(),
                })
    finally:
        _OCR_SEMAPHORE.release()


def start_ocr_async(
    image_bytes: bytes,
    reg_id: Optional[str],
    bbox: Optional[dict],
    is_quick: bool = False,
) -> dict:
    """Create and dispatch an async OCR task. Returns {ok, task_id, status}."""
    logger.info("OCR Async Start called (is_quick=%s, reg_id=%s)", is_quick, reg_id)

    if not image_bytes:
        return {"ok": False, "error": "画像がありません"}

    cleanup_old_ocr_tasks()
    prefix = "ocr_q" if is_quick else "ocr"
    task_id = f"{prefix}_{uuid.uuid4().hex}"
    now = time.time()
    with _OCR_TASKS_LOCK:
        _OCR_TASKS[task_id] = {
            "status": "processing",
            "text": "",
            "fields": {},
            "timing": {},
            "error": None,
            "created_at": now,
            "updated_at": now,
            "is_quick": is_quick,
            "reg_id": reg_id,
            "bbox": bbox,
        }

    if _USE_REDIS_OCR:
        reg_dir = OCR_RUNTIME_DIR / reg_id if reg_id else Path(tempfile.gettempdir()) / "bamboo_ocr_jobs"
        reg_dir.mkdir(parents=True, exist_ok=True)

        img_filename = f"ocr_input_{task_id}.jpg"
        img_path = reg_dir / img_filename
        with open(img_path, "wb") as f:
            f.write(image_bytes)

        task_payload = {
            "task_id": task_id,
            "reg_id": reg_id,
            "image_path": str(img_path.absolute()),
            "bbox": bbox,
            "is_quick": is_quick,
        }
        redis_client.rpush("ocr_tasks", json.dumps(task_payload))
        redis_client.setex(f"ocr_status:{task_id}", 3600, json.dumps(_OCR_TASKS[task_id]))
        logger.info("Task %s pushed to Redis.", task_id)
    else:
        target = _process_quick_ocr_task if is_quick else _process_ocr_task
        t = threading.Thread(target=target, args=(task_id, image_bytes), daemon=True)
        t.start()

    return {"ok": True, "task_id": task_id, "status": "processing"}

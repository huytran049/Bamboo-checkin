"""OCR routes: /api/ocr/*"""
import json
import time
from io import BytesIO
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from flask import Blueprint, request, jsonify

from app_config import logger, _ensure_reader
from card import decode_data_url_to_pil
from services.ocr_service import (
    run_bcard_ocr_from_image,
    cleanup_old_ocr_tasks,
    get_ocr_task_status,
    start_ocr_async,
)
from services.cccd_service import run_cccd_qr_ocr_from_image_bytes

bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")


def _parse_ocr_async_request():
    """Parse image_bytes, reg_id, bbox from an OCR async request."""
    image_bytes: Optional[bytes] = None
    if "image" in request.files:
        image_bytes = request.files["image"].read()
    elif "image_data_url" in request.form:
        img = decode_data_url_to_pil(request.form["image_data_url"]).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        image_bytes = buf.getvalue()
    elif request.is_json:
        js = request.get_json(silent=True) or {}
        if "image_data_url" in js:
            img = decode_data_url_to_pil(js["image_data_url"]).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=90)
            image_bytes = buf.getvalue()

    reg_id = request.form.get("reg_id") or request.args.get("reg_id")
    bbox_raw = request.form.get("bbox") or request.args.get("bbox")

    if request.is_json:
        js = request.get_json(silent=True) or {}
        if not reg_id:
            reg_id = js.get("reg_id")
        if not bbox_raw:
            bbox_raw = js.get("bbox")

    bbox = None
    if bbox_raw:
        try:
            bbox = json.loads(bbox_raw) if isinstance(bbox_raw, str) else bbox_raw
        except Exception:
            logger.warning("Failed to parse bbox: %s", bbox_raw)

    return image_bytes, reg_id, bbox


@bp.post("/bcard_quick")
def ocr_bcard_quick():
    """Quick OCR check - detection only, synchronous response."""
    f = request.files.get("image")
    if not f:
        return jsonify({"ok": False, "error": "Không có ảnh"}), 400
    try:
        ocr_reader = _ensure_reader()
        if ocr_reader is None or getattr(ocr_reader, "engine", None) is None:
            raise RuntimeError("OCR reader is not initialized")
        img = Image.open(f.stream).convert("RGB")
        np_img = np.array(img)
        h, w = np_img.shape[:2]
        max_side = 480
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            np_img = cv2.resize(np_img, (int(w * scale), int(h * scale)))
        t0 = time.time()
        dt_boxes, _ = ocr_reader.engine.text_det(np_img)
        box_count = len(dt_boxes) if dt_boxes is not None else 0
        elapsed = round(time.time() - t0, 3)
        logger.info("bcard_quick (detection only): %d boxes in %.3fs", box_count, elapsed)
        return jsonify({
            "ok": True,
            "box_count": box_count,
            "time": elapsed
        })
    except Exception as e:
        logger.exception("ocr_bcard_quick error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/bcard")
def ocr_bcard():
    t_start = time.time()
    try:
        img: Optional[Image.Image] = None
        if "image" in request.files:
            img = Image.open(request.files["image"].stream)
        elif "image_data_url" in request.form:
            img = decode_data_url_to_pil(request.form["image_data_url"])
        elif request.is_json:
            js = request.get_json(silent=True) or {}
            if "image_data_url" in js:
                img = decode_data_url_to_pil(js["image_data_url"])
        if img is None:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        result = run_bcard_ocr_from_image(img)
        return jsonify({
            "ok": True,
            "text": result["text"],
            "fields": result["fields"],
            "timing": {
                "total": round(time.time() - t_start, 3),
                "ocr": result["timing"]["ocr"],
            },
        })
    except Exception as e:
        logger.exception(f"OCR error: {e}")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/bcard_async/start")
def ocr_bcard_async_start():
    try:
        image_bytes, reg_id, bbox = _parse_ocr_async_request()
        if not image_bytes:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        return jsonify(start_ocr_async(image_bytes, reg_id, bbox, is_quick=False))
    except Exception as e:
        logger.exception("ocr_async_start error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/bcard_async/quick")
def ocr_bcard_async_quick():
    try:
        image_bytes, reg_id, bbox = _parse_ocr_async_request()
        if not image_bytes:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        return jsonify(start_ocr_async(image_bytes, reg_id, bbox, is_quick=True))
    except Exception as e:
        logger.exception("ocr_async_quick error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/bcard_async/status/<task_id>")
def ocr_bcard_async_status(task_id: str):
    try:
        cleanup_old_ocr_tasks()
        rec = get_ocr_task_status(task_id)
        if rec is None:
            return jsonify({"ok": False, "error": "Không tìm thấy tác vụ"}), 404
        return jsonify({"ok": True, **rec})
    except Exception as e:
        logger.exception("ocr_bcard_async_status error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.post("/cccd_qr_ocr")
def ocr_cccd_qr_ocr():
    try:
        image_bytes: Optional[bytes] = None
        if "image" in request.files:
            image_bytes = request.files["image"].read()
        elif "image_data_url" in request.form:
            img = decode_data_url_to_pil(request.form["image_data_url"]).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=90)
            image_bytes = buf.getvalue()
        elif request.is_json:
            js = request.get_json(silent=True) or {}
            if "image_data_url" in js:
                img = decode_data_url_to_pil(js["image_data_url"]).convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=90)
                image_bytes = buf.getvalue()
        if not image_bytes:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        return jsonify(run_cccd_qr_ocr_from_image_bytes(image_bytes))
    except Exception as e:
        logger.exception("ocr_cccd_qr_ocr error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500

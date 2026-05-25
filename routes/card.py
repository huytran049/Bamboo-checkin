"""Card detection routes: /api/card/*"""
import cv2
import numpy as np
from flask import Blueprint, request, jsonify

from app_config import logger, _HAS_CV2, card_detector

bp = Blueprint("card", __name__, url_prefix="/api/card")


@bp.post("/frame")
def card_frame():
    """Auto-detect business card from camera frame (YOLOv8 ONNX)."""
    if not _HAS_CV2:
        return jsonify({"ok": False, "error": "Chưa cài đặt OpenCV"}), 400
    f = request.files.get("frame")
    if not f:
        return jsonify({"ok": False, "error": "Không có khung hình"}), 400
    try:
        frame_bytes = f.read()
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            return jsonify({"ok": False, "error": "Không thể giải mã khung hình"}), 400
        frame_size = {"w": int(frame_bgr.shape[1]), "h": int(frame_bgr.shape[0])}

        triggered, crop_bgr, bbox, ocr_result = card_detector.detect(frame_bgr)

        if not triggered:
            return jsonify({
                "ok": True,
                "card_detected": False,
                "stable_count": card_detector.stable_count,
                "required": card_detector.required_stable,
                "bbox": bbox,
                "frame_size": frame_size,
            })

        check_only = (request.form.get("check_only", "false").lower() == "true")
        if check_only:
            logger.info("Card detected but check_only=True, skipping OCR.")
            return jsonify({
                "ok": True,
                "card_detected": True,
                "stable_count": 0,
                "required": card_detector.required_stable,
                "bbox": bbox,
                "frame_size": frame_size,
                "fields": {},
                "text": ""
            })

        conf_val = (
            bbox.get('conf', 0.0) if isinstance(bbox, dict) else getattr(bbox, 'conf', 0.0)
        )
        logger.info("Card AUTO-CAPTURED bbox=%s conf=%.3f", bbox, conf_val)

        fields = ocr_result if isinstance(ocr_result, dict) else {}
        text = "\n".join([f"{k}: {v}" for k, v in fields.items()]) if fields else ""

        return jsonify({
            "ok": True,
            "card_detected": True,
            "stable_count": 0,
            "required": card_detector.required_stable,
            "bbox": bbox,
            "frame_size": frame_size,
            "fields": fields,
            "text": text,
        })
    except Exception as e:
        logger.exception("card_frame error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500

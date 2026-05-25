"""Registration routes: /api/register, /api/presence/*, /api/registrations/*/qr"""
from flask import Blueprint, request, jsonify, send_from_directory

from app_config import logger, yolo_model, _HAS_YOLO, _YOLO_DEVICE, _HAS_CV2
from database.update_database import get_registration
from face import detect_persons_in_frame, detect_faces_in_frame
from services.registration import save_registration
from services.registration_assets import (
    STATIC_SOUND_DIR,
    RETURNING_VISITOR_GREETING_FILENAME,
    get_registration_greeting_audio_url,
)

bp = Blueprint("registration", __name__)


@bp.post("/api/register")
def register():
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"ok": False, "error": f"JSON không hợp lệ: {e}"}), 400
    return jsonify(save_registration(payload))


@bp.post("/api/presence/payload")
def presence_payload():
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"ok": False, "error": f"JSON không hợp lệ: {e}"}), 400
    return jsonify(save_registration(payload))


@bp.post("/api/presence/frame")
def presence_frame():
    """Detect persons in frame using YOLO, with face-detection fallback for close-up kiosk framing."""
    if not _HAS_CV2:
        return jsonify({"ok": False, "error": "Chưa cài đặt OpenCV"}), 400
    f = request.files.get("frame")
    if not f:
        return jsonify({"ok": False, "error": "Không có khung hình"}), 400
    try:
        frame_bytes = f.read()
        frame_size, boxes, best, yolo_time = detect_persons_in_frame(
            frame_bytes, yolo_model, _HAS_YOLO, _YOLO_DEVICE
        )
        detector = "person_yolo"
        face_time = 0.0

        # In kiosk mode the user may stand very close to the front camera, so YOLO "person"
        # can miss frames that only contain a face/head. Fall back to face detection so the
        # welcome overlay can still dismiss and the flow can continue.
        if not boxes:
            face_frame_size, face_boxes, face_best, face_time = detect_faces_in_frame(frame_bytes)
            if face_boxes:
                frame_size = face_frame_size or frame_size
                boxes = face_boxes
                best = face_best
                detector = "face_fallback"
        return jsonify({
            "ok": True,
            "frame_size": frame_size,
            "boxes": boxes,
            "best": best,
            "yolo_time": yolo_time,
            "face_time": face_time,
            "detector": detector,
        })
    except Exception as e:
        logger.exception("presence_frame error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/api/registrations/<reg_id>/qr")
def api_registration_qr_lookup(reg_id):
    try:
        reg_id = (reg_id or "").strip()
        if not reg_id:
            return jsonify({"ok": False, "error": "registration_id is required"}), 400
        item = get_registration(reg_id)
        if not item:
            return jsonify({"ok": False, "error": "Registration not found"}), 404
        bcard_fields = {
            "full_name": (item.get("full_name") or "").strip(),
            "company": (item.get("company") or "").strip(),
            "email": (item.get("email") or "").strip(),
            "phone": (item.get("phone") or "").strip(),
            "title": (item.get("title") or "").strip(),
            "address": (item.get("address") or "").strip(),
        }
        return jsonify({
            "ok": True,
            "registration_id": item.get("registration_id"),
            "display_name": item.get("full_name") or "",
            "fullName": item.get("full_name") or "",
            "data": {
                "fullName": item.get("full_name") or "",
                "idNumber": item.get("idNumber") or "",
                "oldId": item.get("oldId") or "",
                "dob": item.get("dob") or "",
                "issued": item.get("issued") or "",
                "gender": item.get("gender") or "",
                "address": item.get("address") or "",
                "expiry": item.get("expiry") or "",
            },
            "bcard_fields": bcard_fields,
            "last_bcard_text": item.get("last_bcard_text") or "",
            "greeting_audio_url": get_registration_greeting_audio_url(reg_id),
        })
    except Exception as e:
        logger.exception("api_registration_qr_lookup error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/api/registrations/<reg_id>/greeting-audio")
def api_registration_greeting_audio(reg_id):
    try:
        audio_path = STATIC_SOUND_DIR / RETURNING_VISITOR_GREETING_FILENAME
        if not audio_path.exists():
            return jsonify({"ok": False, "error": "Greeting audio not found"}), 404
        return send_from_directory(str(STATIC_SOUND_DIR.resolve()), RETURNING_VISITOR_GREETING_FILENAME)
    except Exception as e:
        logger.exception("api_registration_greeting_audio error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500

"""Face recognition routes: /api/face/*"""
import json
from flask import Blueprint, request, jsonify, Response

from app_config import (
    logger,
    _HAS_CV2,
    _HAS_REDIS,
    redis_client,
    _USE_REDIS_FACE,
    _FACE_REGISTER_QUEUE,
    _FACE_RECOGNIZE_QUEUE,
    _FACE_RECOGNITION_THRESHOLD,
)
from database.update_database import get_face_db_stats
from env_settings import get_dashboard_settings
from face import detect_faces_in_frame, draw_boxes_on_frame, get_face_embedding_engine
from face.vision import vision_face_helper_available
from routes.helpers import extract_uploaded_image_bytes
from services.face_service import (
    enqueue_face_task,
    get_face_task_status,
    cleanup_old_face_tasks,
)

bp = Blueprint("face", __name__, url_prefix="/api/face")


@bp.post("/frame")
def face_frame():
    """Detect faces in frame using Apple Vision."""
    if not _HAS_CV2:
        return jsonify({"ok": False, "error": "Chưa cài đặt OpenCV"}), 400
    f = request.files.get("frame")
    if not f:
        return jsonify({"ok": False, "error": "Không có khung hình"}), 400
    try:
        frame_bytes = f.read()
        frame_size, boxes, best, face_time = detect_faces_in_frame(frame_bytes)
        return jsonify({
            "ok": True,
            "frame_size": frame_size,
            "boxes": boxes,
            "best": best,
            "face_time": face_time,
        })
    except Exception as e:
        logger.exception("face_frame error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/frame_with_boxes")
def face_frame_with_boxes():
    """Detect faces and return frame with drawn bounding boxes (JPEG)."""
    if not _HAS_CV2:
        return jsonify({"ok": False, "error": "Chưa cài đặt OpenCV"}), 400
    f = request.files.get("frame")
    if not f:
        return jsonify({"ok": False, "error": "Không có khung hình"}), 400
    try:
        frame_bytes = f.read()
        frame_size, boxes, best, _ = detect_faces_in_frame(frame_bytes)
        img_bytes = draw_boxes_on_frame(
            frame_bytes, boxes, best,
            box_color=(0, 255, 0),
            best_color=(0, 0, 255),
        )
        if img_bytes is None:
            return jsonify({"ok": False, "error": "Không thể vẽ khung nhận diện"}), 500
        resp = Response(img_bytes, mimetype="image/jpeg", headers={"Content-Type": "image/jpeg"})
        if best is not None:
            resp.headers["X-Face-Best"] = json.dumps(best)
        if frame_size is not None:
            resp.headers["X-Frame-Size"] = json.dumps(frame_size)
        return resp
    except Exception as e:
        logger.exception("face_frame_with_boxes error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/register_async")
def face_register_async():
    try:
        image_bytes = extract_uploaded_image_bytes()
        js = request.get_json(silent=True) if request.is_json else {}
        registration_id = (
            request.form.get("registration_id")
            or request.args.get("registration_id")
            or (js or {}).get("registration_id")
        )
        registration_id = (registration_id or "").strip()
        if not registration_id:
            return jsonify({"ok": False, "error": "registration_id là bắt buộc"}), 400
        if not image_bytes:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        job_id, image_path = enqueue_face_task(
            task_type="register",
            image_bytes=image_bytes,
            registration_id=registration_id,
        )
        return jsonify({
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "registration_id": registration_id,
            "image_path": image_path,
        })
    except Exception as exc:
        logger.exception("face_register_async error")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.post("/recognize_async")
def face_recognize_async():
    try:
        if not get_dashboard_settings().get("face_recognition_enabled", True):
            return jsonify({"ok": False, "error": "Face recognition is disabled in settings"}), 403
        image_bytes = extract_uploaded_image_bytes()
        if not image_bytes:
            return jsonify({"ok": False, "error": "Không có ảnh"}), 400
        job_id, image_path = enqueue_face_task(task_type="recognize", image_bytes=image_bytes)
        return jsonify({
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "image_path": image_path,
        })
    except Exception as exc:
        logger.exception("face_recognize_async error")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/job/<job_id>")
def face_job_status(job_id: str):
    try:
        cleanup_old_face_tasks()
        rec = get_face_task_status(job_id)
        if rec is None:
            return jsonify({"ok": False, "error": "Không tìm thấy tác vụ"}), 404
        return jsonify({"ok": True, **rec})
    except Exception as exc:
        logger.exception("face_job_status error")
        return jsonify({"ok": False, "error": str(exc)}), 500


@bp.get("/status")
def face_status():
    try:
        queue_size_register = None
        queue_size_recognize = None
        if _HAS_REDIS:
            queue_size_register = int(redis_client.llen(_FACE_REGISTER_QUEUE))
            queue_size_recognize = int(redis_client.llen(_FACE_RECOGNIZE_QUEUE))
        engine = get_face_embedding_engine()
        return jsonify({
            "ok": True,
            "detector_ready": vision_face_helper_available(),
            "detector_backend": "apple_vision",
            "feature_enabled": get_dashboard_settings().get("face_recognition_enabled", True),
            "recognition_ready": engine.is_ready(),
            "redis_ready": _HAS_REDIS,
            "redis_queue_enabled": _USE_REDIS_FACE,
            "queues": {
                "register": queue_size_register,
                "recognize": queue_size_recognize,
            },
            "db": get_face_db_stats(),
            "threshold": _FACE_RECOGNITION_THRESHOLD,
        })
    except Exception as exc:
        logger.exception("face_status error")
        return jsonify({"ok": False, "error": str(exc)}), 500

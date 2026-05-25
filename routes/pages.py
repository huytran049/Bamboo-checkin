"""Pages and static routes: /, /login, /dashboard, /api/status, static files."""
import os
from flask import Blueprint, render_template, jsonify, send_from_directory, Response, request

from app_config import (
    logger, _ensure_reader, REG_DIR,
    _HAS_YOLO, yolo_model,
)
from card import _torch_has_cuda, _torch_has_directml, _lazy_llm
from database.update_database import (
    list_appointments_for_date,
    create_appointment,
)
from env_settings import get_kiosk_language, update_env_values
from routes.helpers import current_user, login_required

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    appointment_overlay_enabled = (os.getenv("APPOINTMENT_OVERLAY_ENABLED", "false") or "false").strip().lower() == "true"
    return render_template("index.html", appointment_overlay_enabled=appointment_overlay_enabled)


@bp.get("/qa-voice-demo")
def qa_voice_demo():
    return render_template("qa_voice_demo.html")


@bp.get("/qa")
def qa_voice_demo_alias():
    return render_template("qa_voice_demo.html")


@bp.get("/api/kiosk/language")
def api_kiosk_language():
    """Public endpoint — trả về ngôn ngữ hiện tại của kiosk."""
    lang = get_kiosk_language()
    return jsonify({"ok": True, "language": lang, "japanese_mode": lang == "ja"})


@bp.put("/api/kiosk/language")
def api_kiosk_language_update():
    """Public endpoint — cho phép đổi ngôn ngữ kiosk giữa vi/ja."""
    js = request.get_json(silent=True) or {}
    raw_language = (js.get("language") or "").strip().lower()
    language = "ja" if raw_language == "ja" else "vi"
    update_env_values({"KIOSK_LANGUAGE": language})
    return jsonify({"ok": True, "language": language, "japanese_mode": language == "ja"})


@bp.get("/favicon.ico")
def favicon():
    return Response(status=204)


@bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("index_dashboard.html", current_user=current_user())


@bp.get("/login")
def login():
    from flask import redirect, url_for
    if current_user():
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@bp.get("/registrations/<reg_id>/<path:fname>")
def serve_registration(reg_id, fname):
    return send_from_directory(REG_DIR / reg_id, fname)


@bp.get("/api/status")
def status():
    ocr_reader = _ensure_reader()
    try:
        import onnxruntime as ort
        ort_avail = ort.get_available_providers()
    except Exception:
        ort_avail = []
    return jsonify({
        "ok": True,
        "ai_ready": bool(_lazy_llm()),
        "ocr_ready": bool(ocr_reader and getattr(ocr_reader, "engine", None)),
        "yolo_ready": bool(_HAS_YOLO and yolo_model),
        "cuda": _torch_has_cuda(),
        "directml": _torch_has_directml(),
        "onnx_providers_available": ort_avail,
    })


@bp.get("/api/kiosk/settings")
def kiosk_settings():
    appointment_overlay_enabled = (os.getenv("APPOINTMENT_OVERLAY_ENABLED", "false") or "false").strip().lower() == "true"
    return jsonify({
        "ok": True,
        "settings": {
            "appointment_overlay_enabled": appointment_overlay_enabled,
        },
    })


@bp.get("/api/appointments/day")
def kiosk_appointments_day():
    overlay_enabled = (os.getenv("APPOINTMENT_OVERLAY_ENABLED", "false") or "false").strip().lower()
    # Keep the endpoint public but only usable when overlay booking is enabled.
    if overlay_enabled != "true":
        return jsonify({"ok": False, "error": "appointment overlay is disabled"}), 403
    date_value = (request.args.get("date") or "").strip()
    if not date_value:
        return jsonify({"ok": False, "error": "date is required"}), 400
    try:
        items = list_appointments_for_date(date_value)
        return jsonify({"ok": True, "items": items})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("kiosk_appointments_day error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.post("/api/appointments")
def kiosk_appointments_create():
    overlay_enabled = (os.getenv("APPOINTMENT_OVERLAY_ENABLED", "false") or "false").strip().lower() == "true"
    if not overlay_enabled:
        return jsonify({"ok": False, "error": "appointment overlay is disabled"}), 403
    js = request.get_json(silent=True) or {}
    try:
        item = create_appointment(
            appointment_date=(js.get("appointment_date") or "").strip(),
            title=(js.get("title") or "").strip(),
            start_time=(js.get("start_time") or "").strip(),
            end_time=(js.get("end_time") or "").strip(),
            description=(js.get("description") or "").strip(),
            contact_name=(js.get("contact_name") or "").strip(),
            appointment_type=(js.get("appointment_type") or "").strip(),
            appointment_reason=(js.get("appointment_reason") or "").strip(),
            registration_id=(js.get("registration_id") or "").strip(),
            source=(js.get("source") or "kiosk").strip(),
        )
        return jsonify({"ok": True, "item": item}), 201
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("kiosk_appointments_create error")
        return jsonify({"ok": False, "error": str(e)}), 500

"""Dashboard routes: /api/dashboard/*"""
from flask import Blueprint, request, jsonify, Response

from app_config import logger
from database.update_database import (
    list_registrations,
    get_registration,
    delete_registration,
    delete_registrations,
    update_registration,
    dashboard_stats,
    list_recent_registrations,
    list_cccd_registrations,
    get_cccd_registration,
    delete_cccd_registration,
    delete_cccd_registrations,
    update_cccd_registration,
    list_appointments_for_month,
    list_appointments_for_date,
    create_appointment,
    update_appointment,
    delete_appointment,
)
from env_settings import get_dashboard_settings, update_env_values, get_kiosk_language
from routes.helpers import login_required, current_user
from services.export_service import build_xlsx_bytes, build_jsonl_body, build_cccd_xlsx_bytes, build_cccd_json_body

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _appointment_actor_name() -> str:
    user = current_user() or {}
    return (user.get("display_name") or user.get("username") or "").strip()


@bp.get("/stats")
@login_required
def api_dashboard_stats():
    try:
        stats = dashboard_stats()
        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        logger.exception("api_dashboard_stats error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/settings")
@login_required
def api_dashboard_settings():
    try:
        return jsonify({"ok": True, "settings": get_dashboard_settings()})
    except Exception as e:
        logger.exception("api_dashboard_settings error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.put("/settings")
@login_required
def api_dashboard_settings_update():
    try:
        js = request.get_json(silent=True) or {}
        updates = {}

        if "face_recognition_enabled" in js:
            updates["FACE_USE_REDIS"] = "0" if bool(js.get("face_recognition_enabled")) else "1"

        if "qr_print_enabled" in js:
            updates["QR_PRINT_ENABLED"] = "true" if bool(js.get("qr_print_enabled")) else "false"

        if "appointment_overlay_enabled" in js:
            updates["APPOINTMENT_OVERLAY_ENABLED"] = "true" if bool(js.get("appointment_overlay_enabled")) else "false"

        if "japanese_mode" in js:
            updates["KIOSK_LANGUAGE"] = "ja" if bool(js.get("japanese_mode")) else "vi"

        if not updates:
            return jsonify({"ok": False, "error": "No valid settings supplied"}), 400

        update_env_values(updates)
        return jsonify({"ok": True, "settings": get_dashboard_settings()})
    except Exception as e:
        logger.exception("api_dashboard_settings_update error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.get("/registrations")
@login_required
def api_dashboard_registrations():
    search = (request.args.get("search") or "").strip()
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=10, type=int)
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    missing_only = request.args.get("missing_only", default=0, type=int) == 1
    try:
        payload = list_registrations(
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            missing_only=missing_only,
        )
        return jsonify({"ok": True, **payload})
    except Exception as e:
        logger.exception("api_dashboard_registrations error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/registrations/<reg_id>")
@login_required
def api_dashboard_registration_detail(reg_id):
    try:
        item = get_registration(reg_id)
        if not item:
            return jsonify({"ok": False, "error": "Không tìm thấy bản đăng ký"}), 404
        return jsonify({"ok": True, "item": item})
    except Exception as e:
        logger.exception("api_dashboard_registration_detail error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.delete("/registrations/<reg_id>")
@login_required
def api_dashboard_registration_delete(reg_id):
    try:
        deleted = delete_registration(reg_id)
        if not deleted:
            return jsonify({"ok": False, "error": "Không tìm thấy bản đăng ký"}), 404
        return jsonify({"ok": True, "deleted": reg_id})
    except Exception as e:
        logger.exception("api_dashboard_registration_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/registrations/bulk-delete")
@login_required
def api_dashboard_registration_bulk_delete():
    try:
        js = request.get_json(silent=True) or {}
        reg_ids = js.get("registration_ids") or []
        deleted_count = delete_registrations(reg_ids if isinstance(reg_ids, list) else [])
        return jsonify({"ok": True, "deleted_count": deleted_count})
    except Exception as e:
        logger.exception("api_dashboard_registration_bulk_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.put("/registrations/<reg_id>")
@login_required
def api_dashboard_registration_update(reg_id):
    try:
        js = request.get_json(silent=True) or {}
        updates = {}
        for key in ("full_name", "company", "email", "phone", "title"):
            if key in js:
                updates[key] = (js.get(key) or "").strip()
        updated = update_registration(reg_id, updates)
        if not updated:
            return jsonify({"ok": False, "error": "Registration not found"}), 404
        return jsonify({"ok": True, "updated": reg_id})
    except Exception as e:
        logger.exception("api_dashboard_registration_update error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.get("/notifications")
@login_required
def api_dashboard_notifications():
    limit = request.args.get("limit", default=10, type=int)
    try:
        items = list_recent_registrations(limit=limit)
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        logger.exception("api_dashboard_notifications error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/appointments/month")
@login_required
def api_dashboard_appointments_month():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    status = (request.args.get("status") or "").strip()
    assignee = (request.args.get("assignee") or "").strip()
    if not year or not month:
        return jsonify({"ok": False, "error": "year and month are required"}), 400
    try:
        items = list_appointments_for_month(year=year, month=month, status=status, assignee=assignee)
        return jsonify({"ok": True, "items": items})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("api_dashboard_appointments_month error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/appointments/day")
@login_required
def api_dashboard_appointments_day():
    appointment_date = (request.args.get("date") or "").strip()
    status = (request.args.get("status") or "").strip()
    assignee = (request.args.get("assignee") or "").strip()
    if not appointment_date:
        return jsonify({"ok": False, "error": "date is required"}), 400
    try:
        items = list_appointments_for_date(appointment_date, status=status, assignee=assignee)
        return jsonify({"ok": True, "items": items})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("api_dashboard_appointments_day error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/appointments")
@login_required
def api_dashboard_appointments_create():
    js = request.get_json(silent=True) or {}
    try:
        actor_name = _appointment_actor_name()
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
            person_id=(js.get("person_id") or "").strip(),
            meeting_id=(js.get("meeting_id") or "").strip(),
            source=(js.get("source") or "dashboard").strip(),
            status=(js.get("status") or "pending").strip(),
            assignee=(js.get("assignee") or "").strip(),
            created_by=actor_name,
            updated_by=actor_name,
        )
        return jsonify({"ok": True, "item": item}), 201
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("api_dashboard_appointments_create error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.put("/appointments/<int:appointment_id>")
@login_required
def api_dashboard_appointments_update(appointment_id):
    js = request.get_json(silent=True) or {}
    try:
        allowed = {
            "appointment_date",
            "start_time",
            "end_time",
            "title",
            "description",
            "contact_name",
            "appointment_type",
            "appointment_reason",
            "registration_id",
            "person_id",
            "meeting_id",
            "source",
            "status",
            "assignee",
        }
        updates = {}
        for key in allowed:
            if key in js:
                updates[key] = (js.get(key) or "").strip()
        updates["updated_by"] = _appointment_actor_name()
        item = update_appointment(appointment_id, updates)
        if not item:
            return jsonify({"ok": False, "error": "appointment not found"}), 404
        return jsonify({"ok": True, "item": item})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("api_dashboard_appointments_update error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.delete("/appointments/<int:appointment_id>")
@login_required
def api_dashboard_appointments_delete(appointment_id):
    try:
        deleted = delete_appointment(appointment_id)
        if not deleted:
            return jsonify({"ok": False, "error": "appointment not found"}), 404
        return jsonify({"ok": True, "deleted": appointment_id})
    except Exception as e:
        logger.exception("api_dashboard_appointments_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/export.xlsx")
@login_required
def api_dashboard_export():
    search = (request.args.get("search") or "").strip()
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    missing_only = request.args.get("missing_only", default=0, type=int) == 1
    try:
        payload = list_registrations(
            search=search,
            page=1,
            page_size=10000,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            missing_only=missing_only,
        )
        xlsx_bytes = build_xlsx_bytes(payload.get("items", []))
        return Response(
            xlsx_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=dashboard_export.xlsx"},
        )
    except Exception as e:
        logger.exception("api_dashboard_export error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/export.jsonl")
@login_required
def api_dashboard_export_jsonl():
    search = (request.args.get("search") or "").strip()
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    missing_only = request.args.get("missing_only", default=0, type=int) == 1
    try:
        payload = list_registrations(
            search=search,
            page=1,
            page_size=10000,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            missing_only=missing_only,
        )
        body = build_jsonl_body(payload.get("items", []))
        return Response(
            body,
            mimetype="application/x-ndjson; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=dashboard_export.jsonl"},
        )
    except Exception as e:
        logger.exception("api_dashboard_export_jsonl error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/cccd")
@login_required
def api_dashboard_cccd():
    search = (request.args.get("search") or "").strip()
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=10, type=int)
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    try:
        payload = list_cccd_registrations(
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return jsonify({"ok": True, **payload})
    except Exception as e:
        logger.exception("api_dashboard_cccd error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/cccd/<reg_id>")
@login_required
def api_dashboard_cccd_detail(reg_id):
    try:
        item = get_cccd_registration(reg_id)
        if not item:
            return jsonify({"ok": False, "error": "CCCD not found"}), 404
        return jsonify({"ok": True, "item": item})
    except Exception as e:
        logger.exception("api_dashboard_cccd_detail error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.delete("/cccd/<reg_id>")
@login_required
def api_dashboard_cccd_delete(reg_id):
    try:
        deleted = delete_cccd_registration(reg_id)
        if not deleted:
            return jsonify({"ok": False, "error": "CCCD not found"}), 404
        return jsonify({"ok": True, "deleted": reg_id})
    except Exception as e:
        logger.exception("api_dashboard_cccd_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.post("/cccd/bulk-delete")
@login_required
def api_dashboard_cccd_bulk_delete():
    try:
        js = request.get_json(silent=True) or {}
        reg_ids = js.get("registration_ids") or []
        deleted_count = delete_cccd_registrations(reg_ids if isinstance(reg_ids, list) else [])
        return jsonify({"ok": True, "deleted_count": deleted_count})
    except Exception as e:
        logger.exception("api_dashboard_cccd_bulk_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.put("/cccd/<reg_id>")
@login_required
def api_dashboard_cccd_update(reg_id):
    try:
        js = request.get_json(silent=True) or {}
        updates = {}
        for key in ("id_number", "old_id", "full_name", "dob", "gender", "address", "issued", "expiry"):
            if key in js:
                updates[key] = (js.get(key) or "").strip()
        updated = update_cccd_registration(reg_id, updates)
        if not updated:
            return jsonify({"ok": False, "error": "CCCD not found"}), 404
        return jsonify({"ok": True, "updated": reg_id})
    except Exception as e:
        logger.exception("api_dashboard_cccd_update error")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.get("/cccd/export.json")
@login_required
def api_dashboard_cccd_export_json():
    search = (request.args.get("search") or "").strip()
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    try:
        payload = list_cccd_registrations(
            search=search,
            page=1,
            page_size=10000,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        body = build_cccd_json_body(payload.get("items", []))
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=cccd_export.json"},
        )
    except Exception as e:
        logger.exception("api_dashboard_cccd_export_json error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500


@bp.get("/cccd/export.xlsx")
@login_required
def api_dashboard_cccd_export_xlsx():
    search = (request.args.get("search") or "").strip()
    sort_by = request.args.get("sort_by", default="created_at", type=str)
    sort_dir = request.args.get("sort_dir", default="desc", type=str)
    try:
        payload = list_cccd_registrations(
            search=search,
            page=1,
            page_size=10000,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        xlsx_bytes = build_cccd_xlsx_bytes(payload.get("items", []))
        return Response(
            xlsx_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=cccd_export.xlsx"},
        )
    except Exception as e:
        logger.exception("api_dashboard_cccd_export_xlsx error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500

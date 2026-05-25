from flask import Blueprint, jsonify, request

from app_config import logger
from services.cccd_service import save_cccd_draft

bp = Blueprint("cccd", __name__, url_prefix="/api/cccd")


@bp.post("/draft")
def cccd_draft():
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"ok": False, "error": f"JSON không hợp lệ: {e}"}), 400

    try:
        return jsonify(save_cccd_draft(payload))
    except Exception as e:
        logger.exception("cccd_draft error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {e}"}), 500

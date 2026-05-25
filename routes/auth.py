"""Auth routes: /api/auth/*"""
from flask import Blueprint, request, jsonify, session

from app_config import logger
from database.update_database import authenticate_user
from routes.helpers import current_user

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def api_auth_login():
    js = request.get_json(silent=True) or {}
    username = (js.get("username") or request.form.get("username") or "").strip()
    password = (js.get("password") or request.form.get("password") or "").strip()
    if not username or not password:
        return jsonify({"ok": False, "error": "Tên đăng nhập và mật khẩu là bắt buộc"}), 400
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"ok": False, "error": "Thông tin đăng nhập không hợp lệ"}), 401
    session["user"] = user
    return jsonify({"ok": True, "user": user})


@bp.post("/logout")
def api_auth_logout():
    session.pop("user", None)
    return jsonify({"ok": True})


@bp.get("/me")
def api_auth_me():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
    return jsonify({"ok": True, "user": user})

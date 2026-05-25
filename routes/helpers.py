"""
Shared route helpers: auth utilities and request parsing.
"""
from io import BytesIO
from functools import wraps
from typing import Optional

from flask import request, jsonify, session, redirect, url_for

from app_config import logger
from card import decode_data_url_to_pil


def current_user():
    return session.get("user")


def login_required(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        if current_user():
            return fn(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        return redirect(url_for("pages.login"))
    return _wrapped


def extract_uploaded_image_bytes() -> Optional[bytes]:
    """Extract image bytes from multipart, form, or JSON request."""
    image_bytes = None
    if "image" in request.files:
        image_bytes = request.files["image"].read()
    elif "frame" in request.files:
        image_bytes = request.files["frame"].read()
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
    return image_bytes

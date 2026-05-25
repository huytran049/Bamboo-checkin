"""
Bamboo Kiosk — Flask application entry point.
App factory, shared middleware, and blueprint registration.
"""
import os
import time
from flask import Flask, g, request, jsonify, session
from flask_cors import CORS

from app_config import logger, warmup
from routes import register_blueprints

# ================= Flask App Factory =================
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "bamboo-kiosk-secret")

import logging as _logging
_logging.getLogger("werkzeug").setLevel(_logging.INFO)
app.logger.setLevel(_logging.INFO)


# ================= Middleware =================
@app.before_request
def _log_request_start():
    g._request_started_at = time.perf_counter()
    cl = request.content_length or 0
    size_str = f" sz={cl/1024:.1f}KB" if cl > 0 else ""
    logger.info("REQ %s %s from=%s%s", request.method, request.full_path, request.remote_addr, size_str)


@app.errorhandler(413)
def request_entity_too_large(error):
    logger.error("!!! 413 Request Entity Too Large: %s (Size: %s)", request.path, request.content_length)
    return jsonify({"ok": False, "error": "Request entity too large (payload too big)"}), 413


@app.after_request
def _log_request_end(response):
    started_at = getattr(g, "_request_started_at", None)
    if started_at is not None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info("RES %s %s status=%s %.1fms", request.method, request.path, response.status_code, elapsed_ms)
    else:
        logger.info("RES %s %s status=%s", request.method, request.path, response.status_code)
    return response


# ================= Blueprint Registration =================
register_blueprints(app)


# ================= Entry Point =================
APP_BIND_HOST = os.getenv("HOST", "0.0.0.0")
APP_PORT = int(os.getenv("PORT", "5000"))
APP_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
APP_USE_RELOADER = os.getenv("FLASK_RELOADER", "0") == "1"

if __name__ == "__main__":
    try:
        warmup()
    except Exception as e:
        logger.warning(f"Warmup failed: {e}")
    app.run(
        host=APP_BIND_HOST,
        port=APP_PORT,
        debug=APP_DEBUG,
        use_reloader=APP_USE_RELOADER,
        threaded=True,
    )

"""
Shared configuration, global state, and model initialization.
All services import shared state from this module.
"""
import os
import logging
import threading

import numpy as np
import redis as redis_lib
from pathlib import Path
from dotenv import load_dotenv

from card import CardYoloCapture, get_reader, init_yolo

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)

# ── CV2 (conditional) ────────────────────────────────────
try:
    import cv2
    _HAS_CV2 = True
except Exception:
    cv2 = None
    _HAS_CV2 = False

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "kiosk.log")
    ]
)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

logging.getLogger("ultralytics").setLevel(logging.WARNING)
logging.captureWarnings(True)

for _name in ("rapidocr_onnxruntime", "onnxruntime", "werkzeug"):
    _lg = logging.getLogger(_name)
    _lg.setLevel(logging.INFO)
    _lg.handlers.clear()
    _lg.propagate = True

logger = logging.getLogger("kiosk")

# ── OCR Readers ──────────────────────────────────────────
reader = None
_QUICK_READER = None


def _get_quick_reader():
    """Lazy initialization of a DEFAULT RapidOCR instance (without wrapper)."""
    global _QUICK_READER
    if _QUICK_READER is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _QUICK_READER = RapidOCR()
            logger.info("Initialized DEFAULT RapidOCR engine for Quick OCR.")
        except Exception as e:
            logger.error(f"Failed to init DEFAULT RapidOCR: {e}")
            return None
    return _QUICK_READER


def _ensure_reader():
    """Initialize the main OCR reader lazily and return it when available."""
    global reader
    if reader is None or getattr(reader, "engine", None) is None:
        reader = get_reader()
    return reader


# ── AI Flags ─────────────────────────────────────────────
AI_READY = False
ENABLE_LLM = os.getenv("ENABLE_LLM", "0") == "1"

# ── Card Detector (YOLOv8 ONNX) ─────────────────────────
_CARD_MODEL_PATH = os.path.join("models", "card", "best.onnx")
card_detector = CardYoloCapture(
    model_path=_CARD_MODEL_PATH,
    required_stable=16,
    conf_threshold=0.92,
    cooldown=3.0,
    infer_size=640,
    use_swift_ocr=False,
)

# ── Redis ────────────────────────────────────────────────
try:
    redis_client = redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    _HAS_REDIS = True
    logger.info("Redis connection established.")
except Exception as re_err:
    redis_client = None
    _HAS_REDIS = False
    logger.warning(f"Redis not available: {re_err}. Falling back to in-memory/threads if possible.")

_USE_REDIS_OCR = os.getenv("OCR_USE_REDIS", "0") == "1" and _HAS_REDIS
_USE_REDIS_FACE = os.getenv("FACE_USE_REDIS", "0") == "1" and _HAS_REDIS
if _HAS_REDIS and not _USE_REDIS_OCR:
    logger.info("Redis is available but OCR async will use in-process threads because OCR_USE_REDIS=0.")
if _HAS_REDIS and not _USE_REDIS_FACE:
    logger.info("Redis is available but face async will use in-process threads because FACE_USE_REDIS=0.")

# ── Task Stores ──────────────────────────────────────────
_OCR_TASKS: dict[str, dict] = {}
_OCR_TASKS_LOCK = threading.Lock()
_OCR_TASK_TTL_SEC = 600
_OCR_SEMAPHORE = threading.Semaphore(6)

_FACE_TASKS: dict[str, dict] = {}
_FACE_TASKS_LOCK = threading.Lock()
_FACE_TASK_TTL_SEC = 3600
_FACE_REGISTER_QUEUE = "face_register_tasks"
_FACE_RECOGNIZE_QUEUE = "face_recognize_tasks"
_FACE_STATUS_PREFIX = "face_status:"
_FACE_RECOGNITION_THRESHOLD = float(os.getenv("FACE_RECOGNITION_THRESHOLD", "0.40"))

# ── Eager Init (order matters: quick reader → load_dotenv → main reader) ──
_ = _get_quick_reader()
load_dotenv()
reader = _ensure_reader()

# ── Paths ────────────────────────────────────────────────
REG_DIR = Path("registrations")
REG_DIR.mkdir(exist_ok=True, parents=True)
_FACE_HELPER_PATH = (Path(__file__).resolve().parent / "helpers" / "face_worker_helper.py").resolve()

# ── SQLite Init ──────────────────────────────────────────
from database.update_database import setup_database as init_sqlite_db

try:
    _init_conn = init_sqlite_db()
    if _init_conn is not None:
        _init_conn.close()
    logger.info("SQLite database initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize SQLite database: {e}")

# ── Forward Config ───────────────────────────────────────
FORWARD_ENABLED = os.getenv("FORWARD_ENABLED", "false").lower() == "true"
FORWARD_URL = os.getenv("FORWARD_URL", "").strip()
FORWARD_API_KEY = os.getenv("FORWARD_API_KEY", "").strip()

# ── YOLO ─────────────────────────────────────────────────
_HAS_YOLO = False
yolo_model = None
_YOLO_DEVICE = "cpu"

try:
    yolo_model, _HAS_YOLO = init_yolo()
except Exception as e:
    logger.warning(f"YOLO initialization failed: {e}")


# ── Warmup ───────────────────────────────────────────────
def warmup():
    """Warm up models for faster first-call performance."""
    global AI_READY
    ocr_reader = _ensure_reader()

    if _HAS_YOLO and yolo_model is not None:
        try:
            z = np.zeros((320, 320, 3), dtype=np.uint8)
            yolo_model(z, verbose=False, device=_YOLO_DEVICE)

            is_swift_reader = bool(getattr(ocr_reader, "worker_path", None))
            if (not is_swift_reader) and ocr_reader is not None and getattr(ocr_reader, "engine", None) is not None:
                z_ocr = np.zeros((100, 300, 3), dtype=np.uint8)
                ocr_reader.readtext(z_ocr, detail=0)
                logger.info("OCR engine warmed up.")
            elif is_swift_reader:
                logger.info("Skipping blank-image OCR warmup for Swift OCR worker.")
        except Exception as e:
            logger.warning(f"YOLO warmup err: {e}")

    AI_READY = True

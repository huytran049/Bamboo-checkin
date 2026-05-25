import json
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("kiosk.face.vision")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VISION_FACE_HELPER_PATH = PROJECT_ROOT / "workers_swift" / "vision_face_detector.swift"
SWIFT_BIN = os.getenv("SWIFT_BIN", "swift")
SWIFTC_BIN = os.getenv("SWIFTC_BIN", "swiftc")
VISION_FACE_HELPER_BIN = os.getenv("VISION_FACE_HELPER_BIN", "").strip()
VISION_FACE_HELPER_BUILD_DIR = PROJECT_ROOT / ".build"
VISION_FACE_HELPER_BUILD_PATH = VISION_FACE_HELPER_BUILD_DIR / "vision_face_detector"
_HELPER_CMD_LOCK = threading.Lock()
_HELPER_CMD_CACHE: list[str] | None = None
_HELPER_CMD_SOURCE_MTIME: float | None = None


def vision_face_helper_available() -> bool:
    if VISION_FACE_HELPER_BIN:
        return Path(VISION_FACE_HELPER_BIN).exists()
    return VISION_FACE_HELPER_PATH.exists()


def _build_compiled_helper(source_path: Path) -> list[str] | None:
    try:
        VISION_FACE_HELPER_BUILD_DIR.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [SWIFTC_BIN, "-O", str(source_path), "-o", str(VISION_FACE_HELPER_BUILD_PATH)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode == 0 and VISION_FACE_HELPER_BUILD_PATH.exists():
            logger.info("Compiled Apple Vision face helper: %s", VISION_FACE_HELPER_BUILD_PATH)
            return [str(VISION_FACE_HELPER_BUILD_PATH)]
        stderr = (proc.stderr or proc.stdout or "").strip()
        if stderr:
            logger.warning("Failed to compile Apple Vision helper, falling back to swift script: %s", stderr)
    except Exception as exc:
        logger.warning("Failed to compile Apple Vision helper, falling back to swift script: %s", exc)
    return None


def _resolve_helper_cmd() -> list[str]:
    global _HELPER_CMD_CACHE, _HELPER_CMD_SOURCE_MTIME

    if VISION_FACE_HELPER_BIN:
        custom_bin = Path(VISION_FACE_HELPER_BIN)
        if not custom_bin.exists():
            raise FileNotFoundError(f"Configured Vision face helper binary not found: {custom_bin}")
        return [str(custom_bin)]

    if not VISION_FACE_HELPER_PATH.exists():
        raise FileNotFoundError(f"Vision face helper not found: {VISION_FACE_HELPER_PATH}")

    source_mtime = VISION_FACE_HELPER_PATH.stat().st_mtime
    with _HELPER_CMD_LOCK:
        if _HELPER_CMD_CACHE is not None and _HELPER_CMD_SOURCE_MTIME == source_mtime:
            return list(_HELPER_CMD_CACHE)

        helper_cmd = None
        if VISION_FACE_HELPER_BUILD_PATH.exists():
            binary_mtime = VISION_FACE_HELPER_BUILD_PATH.stat().st_mtime
            if binary_mtime >= source_mtime:
                helper_cmd = [str(VISION_FACE_HELPER_BUILD_PATH)]

        if helper_cmd is None:
            helper_cmd = _build_compiled_helper(VISION_FACE_HELPER_PATH)

        if helper_cmd is None:
            helper_cmd = [SWIFT_BIN, str(VISION_FACE_HELPER_PATH)]

        _HELPER_CMD_CACHE = list(helper_cmd)
        _HELPER_CMD_SOURCE_MTIME = source_mtime
        return list(helper_cmd)


def _run_vision_face_helper(image_path: str | Path) -> dict[str, Any]:
    if not vision_face_helper_available():
        raise FileNotFoundError(f"Vision face helper not found: {VISION_FACE_HELPER_PATH}")

    helper_cmd = _resolve_helper_cmd()
    proc = subprocess.run(
        [*helper_cmd, str(image_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    if proc.returncode != 0:
        raise RuntimeError(stderr or stdout or "Vision face helper failed")
    if not stdout:
        raise RuntimeError(stderr or "Vision face helper returned empty output")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Vision face helper returned invalid JSON: {exc}") from exc


def detect_faces_from_path(image_path: str | Path) -> dict[str, Any]:
    payload = _run_vision_face_helper(image_path)
    return {
        "image_size": payload.get("image_size") or {},
        "faces": payload.get("faces") or [],
    }


def detect_faces_from_bgr(image_bgr: np.ndarray) -> dict[str, Any]:
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("image_bgr is empty")

    success, encoded = cv2.imencode(".jpg", image_bgr)
    if not success:
        raise ValueError("Failed to encode image for Vision helper")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(encoded.tobytes())
        return detect_faces_from_path(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

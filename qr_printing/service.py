import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


logger = logging.getLogger("kiosk.qr_printing")
PRINT_RUNTIME_DIR = Path(".runtime") / "qr_printing"
PRINT_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
PRINT_PROFILE_PATH = Path("qr_printing") / "print_profile.json"
_PRINT_INFLIGHT_LOCK = threading.RLock()
_PRINT_INFLIGHT_REG_IDS: set[str] = set()


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r. Falling back to %s.", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r. Falling back to %s.", name, raw, default)
        return default


def _mm_to_px(mm: float, dpi: int) -> int:
    return max(1, int(round((mm / 25.4) * dpi)))


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw in allowed:
        return raw
    logger.warning("Invalid value for %s=%r. Falling back to %s.", name, raw, default)
    return default


def _resolve_axis_position(axis_length: int, content_length: int, margin_px: int, align: str) -> int:
    available = max(0, axis_length - content_length - (margin_px * 2))
    if align == "start":
        return margin_px
    if align == "end":
        return margin_px + available
    return margin_px + (available // 2)


def _load_print_profile() -> dict:
    defaults = {
        "printer_name": (os.getenv("QR_PRINTER_NAME") or "").strip(),
        "copies": max(1, _env_int("QR_PRINT_COPIES", 1)),
        "page_size": (os.getenv("QR_PRINT_PAGE_SIZE") or "").strip(),
        "media": (os.getenv("QR_PRINT_MEDIA") or "Custom.78x52mm").strip(),
        "fit_to_page": _env_bool("QR_PRINT_FIT_TO_PAGE", True),
        "landscape": _env_bool("QR_PRINT_LANDSCAPE", True),
        "scaling": _env_int("QR_PRINT_SCALING", 100),
        "extra_options": (os.getenv("QR_PRINT_OPTIONS") or "").strip(),
        "command": (os.getenv("QR_PRINT_COMMAND") or "").strip().lower(),
    }
    try:
        if not PRINT_PROFILE_PATH.exists():
            return defaults
        import json
        with PRINT_PROFILE_PATH.open("r", encoding="utf-8") as f:
            loaded = json.load(f) or {}
        return {
            "printer_name": str(loaded.get("printer_name", defaults["printer_name"])).strip(),
            "copies": max(1, int(loaded.get("copies", defaults["copies"]))),
            "page_size": str(loaded.get("page_size", defaults["page_size"])).strip(),
            "media": str(loaded.get("media", defaults["media"])).strip(),
            "fit_to_page": bool(loaded.get("fit_to_page", defaults["fit_to_page"])),
            "landscape": bool(loaded.get("landscape", defaults["landscape"])),
            "scaling": int(loaded.get("scaling", defaults["scaling"])),
            "extra_options": " ".join(str(loaded.get("extra_options", defaults["extra_options"])).split()),
            "command": str(loaded.get("command", defaults["command"])).strip().lower(),
        }
    except Exception as exc:
        logger.warning("Failed to load print profile from %s: %s", PRINT_PROFILE_PATH, exc)
        return defaults


def _build_print_canvas(qr_path: Path, reg_id: str) -> Path:
    dpi = max(72, _env_int("QR_PRINT_DPI", 300))
    width_mm = max(20.0, _env_float("QR_PRINT_WIDTH_MM", 78.0))
    height_mm = max(20.0, _env_float("QR_PRINT_HEIGHT_MM", 52.0))
    margin_mm = max(0.0, _env_float("QR_PRINT_MARGIN_MM", 2.0))
    offset_x_mm = _env_float("QR_PRINT_OFFSET_X_MM", 0.0)
    offset_y_mm = _env_float("QR_PRINT_OFFSET_Y_MM", 0.0)
    align_x = _env_choice("QR_PRINT_ALIGN_X", "center", {"start", "center", "end"})
    align_y = _env_choice("QR_PRINT_ALIGN_Y", "center", {"start", "center", "end"})
    show_reg_id = _env_bool("QR_PRINT_SHOW_REG_ID", False)
    qr_scale = min(1.0, max(0.1, _env_float("QR_PRINT_QR_SCALE", 0.85)))

    canvas_w = _mm_to_px(width_mm, dpi)
    canvas_h = _mm_to_px(height_mm, dpi)
    margin_px = _mm_to_px(margin_mm, dpi)
    offset_x_px = _mm_to_px(abs(offset_x_mm), dpi) * (-1 if offset_x_mm < 0 else 1)
    offset_y_px = _mm_to_px(abs(offset_y_mm), dpi) * (-1 if offset_y_mm < 0 else 1)

    img = Image.new("RGB", (canvas_w, canvas_h), "white")
    qr_img = Image.open(qr_path).convert("RGB")

    text_band_px = int(canvas_h * 0.18) if show_reg_id else 0
    usable_w = max(1, canvas_w - (margin_px * 2))
    usable_h = max(1, canvas_h - (margin_px * 2) - text_band_px)
    qr_size = max(1, int(min(usable_w, usable_h) * qr_scale))

    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    qr_x = _resolve_axis_position(canvas_w, qr_size, margin_px, align_x) + offset_x_px
    qr_y = _resolve_axis_position(canvas_h - text_band_px, qr_size, margin_px, align_y) + offset_y_px
    qr_x = max(0, min(canvas_w - qr_size, qr_x))
    qr_y = max(0, min(canvas_h - text_band_px - qr_size, qr_y))
    img.paste(qr_img, (qr_x, qr_y))

    if show_reg_id:
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        text = reg_id.strip()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = max(margin_px, (canvas_w - text_w) // 2)
        text_y = canvas_h - margin_px - text_h
        draw.text((text_x, text_y), text, fill="black", font=font)

    out_dir = PRINT_RUNTIME_DIR / reg_id.strip()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "registration_qr_print.png"
    img.save(out_path, format="PNG", dpi=(dpi, dpi))
    return out_path


def _build_print_command(print_source_path: Path) -> list[str]:
    profile = _load_print_profile()
    printer_name = profile["printer_name"]
    copies = profile["copies"]
    page_size = profile["page_size"]
    media = profile["media"]
    fit_to_page = profile["fit_to_page"]
    landscape = profile["landscape"]
    scaling = profile["scaling"]
    extra_options = profile["extra_options"]
    command_name = profile["command"]

    if not command_name:
        command_name = "lp" if shutil.which("lp") else "lpr"

    if command_name == "lp":
        cmd = ["lp", "-n", str(copies)]
        if printer_name:
            cmd.extend(["-d", printer_name])
        if page_size:
            cmd.extend(["-o", f"PageSize={page_size}"])
        elif media:
            cmd.extend(["-o", f"media={media}"])
        if landscape:
            cmd.extend(["-o", "orientation-requested=4"])
        if fit_to_page:
            cmd.extend(["-o", "fit-to-page"])
        if scaling > 0:
            cmd.extend(["-o", f"scaling={scaling}"])
        if extra_options:
            for item in extra_options.split():
                cmd.extend(["-o", item])
        cmd.append(str(print_source_path.resolve()))
        return cmd

    cmd = ["lpr", "-#", str(copies)]
    if printer_name:
        cmd.extend(["-P", printer_name])
    if page_size:
        cmd.extend(["-o", f"PageSize={page_size}"])
    elif media:
        cmd.extend(["-o", f"media={media}"])
    if landscape:
        cmd.extend(["-o", "orientation-requested=4"])
    if fit_to_page:
        cmd.extend(["-o", "fit-to-page"])
    if scaling > 0:
        cmd.extend(["-o", f"scaling={scaling}"])
    if extra_options:
        for item in extra_options.split():
            cmd.extend(["-o", item])
    cmd.append(str(print_source_path.resolve()))
    return cmd


def _run_print_job(qr_path: Path, reg_id: str, stamp_path: Path) -> None:
    temp_rendered_path = None
    try:
        use_source_image = _env_bool("QR_PRINT_USE_SOURCE_IMAGE", True)
        if not use_source_image:
            logger.warning(
                "QR_PRINT_USE_SOURCE_IMAGE=false is using legacy canvas rendering for %s. "
                "Preferred mode is printing the already prepared registration_qr.png directly.",
                reg_id,
            )
        print_source_path = qr_path.resolve() if use_source_image else _build_print_canvas(qr_path, reg_id)
        if not use_source_image:
            temp_rendered_path = print_source_path
        cmd = _build_print_command(print_source_path)
        logger.info("Submitting QR print job for %s: %s", reg_id, " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "print command failed").strip())
        stamp_path.write_text("printed\n", encoding="utf-8")
        logger.info("QR print submitted successfully for %s", reg_id)
    except Exception as exc:
        logger.error("QR print failed for %s: %s", reg_id, exc)
    finally:
        with _PRINT_INFLIGHT_LOCK:
            _PRINT_INFLIGHT_REG_IDS.discard(reg_id)
        if temp_rendered_path and temp_rendered_path.exists():
            try:
                temp_rendered_path.unlink()
            except OSError:
                pass


def enqueue_qr_print(qr_path: Path, reg_id: str) -> bool:
    if not _env_bool("QR_PRINT_ENABLED", False):
        return False
    if not qr_path.exists():
        logger.warning("Skipping QR print for %s because QR file does not exist: %s", reg_id, qr_path)
        return False
    if not (shutil.which("lp") or shutil.which("lpr")):
        logger.warning("Skipping QR print for %s because neither lp nor lpr is available.", reg_id)
        return False

    stamp_dir = PRINT_RUNTIME_DIR / reg_id.strip()
    stamp_dir.mkdir(parents=True, exist_ok=True)
    stamp_path = stamp_dir / ".qr_printed"
    allow_reprint = _env_bool("QR_PRINT_ALLOW_REPRINT", False)
    if stamp_path.exists() and not allow_reprint:
        logger.info("Skipping duplicate QR print for %s because .qr_printed already exists.", reg_id)
        return False
    with _PRINT_INFLIGHT_LOCK:
        if reg_id in _PRINT_INFLIGHT_REG_IDS:
            logger.info("Skipping duplicate QR print for %s because a print job is already in flight.", reg_id)
            return False
        _PRINT_INFLIGHT_REG_IDS.add(reg_id)

    run_async = _env_bool("QR_PRINT_ASYNC", True)
    if run_async:
        thread = threading.Thread(
            target=_run_print_job,
            args=(qr_path, reg_id, stamp_path),
            daemon=True,
        )
        thread.start()
    else:
        _run_print_job(qr_path, reg_id, stamp_path)
    return True

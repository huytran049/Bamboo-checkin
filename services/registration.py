"""
Registration business logic: save, QR, greeting, checkin.
Extracted from application.py lines 289-616.
"""
import json
import os
import re
import random
import string
import time
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import qrcode
from PIL import Image

from app_config import logger, REG_DIR
from card import decode_data_url_to_pil
from card.utils import undistort_image
from qr_printing import enqueue_qr_print
from database.update_database import (
    save_to_sqlite_with_retry as save_to_sqlite,
    check_and_trigger_cleanup,
)
from services.face_service import schedule_registration_face_embedding
from services.registration_assets import (
    get_registration_greeting_audio_url,
)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
REGISTRATION_JSON_LOCK = threading.RLock()
QR_LAYOUT_PATH = Path("qr_printing") / "layout.json"


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


def _prune_empty(value):
    if isinstance(value, dict):
        pruned = {}
        for key, item in value.items():
            cleaned = _prune_empty(item)
            if cleaned in (None, "", [], {}):
                continue
            pruned[key] = cleaned
        return pruned
    if isinstance(value, list):
        return [item for item in (_prune_empty(item) for item in value) if item not in (None, "", [], {})]
    return value


def _load_qr_layout() -> dict:
    defaults = {
        "canvas": {
            "width_mm": 40.0,
            "height_mm": 60.0,
            "dpi": 203,
            "background": "white",
        },
        "qr": {
            "size_mm": 34.0,
            "offset_x_mm": 0.0,
            "offset_y_mm": 0.0,
        },
    }
    try:
        if not QR_LAYOUT_PATH.exists():
            return defaults
        with QR_LAYOUT_PATH.open("r", encoding="utf-8") as f:
            loaded = json.load(f) or {}
        canvas = loaded.get("canvas") or {}
        qr = loaded.get("qr") or {}
        return {
            "canvas": {
                "width_mm": float(canvas.get("width_mm", defaults["canvas"]["width_mm"])),
                "height_mm": float(canvas.get("height_mm", defaults["canvas"]["height_mm"])),
                "dpi": int(canvas.get("dpi", defaults["canvas"]["dpi"])),
                "background": str(canvas.get("background", defaults["canvas"]["background"])).strip() or "white",
            },
            "qr": {
                "size_mm": float(qr.get("size_mm", defaults["qr"]["size_mm"])),
                "offset_x_mm": float(qr.get("offset_x_mm", defaults["qr"]["offset_x_mm"])),
                "offset_y_mm": float(qr.get("offset_y_mm", defaults["qr"]["offset_y_mm"])),
            },
        }
    except Exception as exc:
        logger.warning("Failed to load QR layout from %s: %s", QR_LAYOUT_PATH, exc)
        return defaults


def save_image_dataurl(target_folder: Path, name_noext: str, data_url: str, undistort: bool = False) -> Optional[str]:
    try:
        img = decode_data_url_to_pil(data_url).convert("RGB")
        if undistort:
            np_img = np.array(img)
            np_img = undistort_image(np_img)
            img = Image.fromarray(np_img)

        fmt = "PNG"
        if data_url.split(";")[0].endswith(("jpeg", "jpg")):
            fmt = "JPEG"
        out_path = target_folder / f"{name_noext}.{fmt.lower()}"
        img.save(out_path, fmt, quality=92)
        return out_path.name
    except Exception:
        return None


def append_checkin_line(reg_id: str, data: dict, bcard_fields: Optional[dict]):
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    entry: dict[str, object] = {
        "time": now_str,
        "reg_id": reg_id,
        "idNumber": data.get("idNumber", ""),
        "fullName": data.get("fullName", ""),
        "dob": data.get("dob", ""),
        "issued": data.get("issued", ""),
    }
    b = bcard_fields or {}
    entry.update({
        "full_name": b.get("full_name", ""),
        "title": b.get("title", ""),
        "email": b.get("email", ""),
        "company": b.get("company", ""),
        "phone": b.get("phone", ""),
        "address": b.get("address", ""),
    })
    try:
        checkin_path = LOG_DIR / "checkin.txt"
        with checkin_path.open("a", encoding="utf-8") as f:
            f.write("[INFO] " + json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to append checkin.txt: {e}")


def build_identity_fields(payload: dict, bcard_fields: Optional[dict]) -> dict:
    src = bcard_fields or {}
    return {
        "full_name": (src.get("full_name") or src.get("name") or "").strip(),
        "company": (src.get("company") or src.get("org") or "").strip(),
        "email": (src.get("email") or "").strip(),
        "phone": (src.get("phone") or src.get("tel") or "").strip(),
        "title": (src.get("title") or src.get("position") or src.get("role") or "").strip(),
        "address": (src.get("address") or "").strip(),
        "last_bcard_text": (payload.get("last_bcard_text") or "").strip(),
    }


def has_meaningful_bcard_fields(bcard_fields: Optional[dict]) -> bool:
    src = bcard_fields or {}
    return any(
        str(src.get(key) or "").strip()
        for key in ("full_name", "name", "company", "org", "email", "phone", "tel", "title", "position", "role", "address")
    )


def persist_registration_json(reg_folder: Path, enriched: dict) -> None:
    with (reg_folder / "data.json").open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)


def read_registration_json(reg_folder: Path) -> dict:
    data_path = reg_folder / "data.json"
    if not data_path.exists():
        return {}
    try:
        with data_path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as exc:
        logger.warning("Failed to read existing data.json for %s: %s", reg_folder.name, exc)
        return {}


def _build_registration_qr_text(reg_folder: Path, reg_id: str) -> str:
    enriched = read_registration_json(reg_folder)
    data = enriched.get("data") or {}
    bcard_fields = enriched.get("bcard_fields") or {}
    full_name = (
        (bcard_fields.get("full_name") or bcard_fields.get("name") or "").strip()
        or (data.get("fullName") or "").strip()
    )
    company = (bcard_fields.get("company") or bcard_fields.get("org") or "").strip()
    email = (bcard_fields.get("email") or "").strip()
    phone = (bcard_fields.get("phone") or bcard_fields.get("tel") or "").strip()
    title = (bcard_fields.get("title") or bcard_fields.get("position") or bcard_fields.get("role") or "").strip()
    address = ((bcard_fields.get("address") or "").strip() or (data.get("address") or "").strip())
    lines = [f"ID: {(reg_id or '').strip()}"]
    if full_name:
        lines.append(f"Họ tên: {full_name}")
    if company:
        lines.append(f"Công ty: {company}")
    if email:
        lines.append(f"Email: {email}")
    if phone:
        lines.append(f"Điện thoại: {phone}")
    if title:
        lines.append(f"Chức vụ: {title}")
    if address:
        lines.append(f"Địa chỉ: {address}")
    return "\n".join(lines)


def _render_print_ready_registration_qr(payload_text: str, output_path: Path) -> None:
    layout = _load_qr_layout()
    dpi = max(72, int(layout["canvas"]["dpi"]))
    width_mm = max(20.0, float(layout["canvas"]["width_mm"]))
    height_mm = max(20.0, float(layout["canvas"]["height_mm"]))
    canvas_w = _mm_to_px(width_mm, dpi)
    canvas_h = _mm_to_px(height_mm, dpi)
    canvas = Image.new("RGB", (canvas_w, canvas_h), str(layout["canvas"]["background"]))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=12,
        border=4,
    )
    qr.add_data(payload_text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_size = min(
        max(1, _mm_to_px(max(5.0, float(layout["qr"]["size_mm"])), dpi)),
        canvas_w,
        canvas_h,
    )
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    offset_x_px = _mm_to_px(abs(float(layout["qr"]["offset_x_mm"])), dpi) * (-1 if float(layout["qr"]["offset_x_mm"]) < 0 else 1)
    offset_y_px = _mm_to_px(abs(float(layout["qr"]["offset_y_mm"])), dpi) * (-1 if float(layout["qr"]["offset_y_mm"]) < 0 else 1)
    qr_x = max(0, min(canvas_w - qr_size, ((canvas_w - qr_size) // 2) + offset_x_px))
    qr_y = max(0, min(canvas_h - qr_size, ((canvas_h - qr_size) // 2) + offset_y_px))
    canvas.paste(qr_img, (qr_x, qr_y))
    canvas.save(output_path, format="PNG", dpi=(dpi, dpi))


def update_registration_json(reg_folder: Path, updater) -> dict:
    reg_folder.mkdir(exist_ok=True, parents=True)
    with REGISTRATION_JSON_LOCK:
        existing = read_registration_json(reg_folder)
        enriched = updater(existing or {}) or {}
        persist_registration_json(reg_folder, enriched)
        return enriched


def generate_registration_qr(reg_folder: Path, reg_id: str, *, submit_print: bool = False) -> Optional[str]:
    reg_id = (reg_id or "").strip()
    if not reg_id:
        return None
    try:
        qr_filename = "registration_qr.png"
        qr_path = reg_folder / qr_filename
        qr_text = _build_registration_qr_text(reg_folder, reg_id)
        _render_print_ready_registration_qr(qr_text, qr_path)
        should_print_now = submit_print or (os.getenv("QR_PRINT_ENABLED", "false").strip().lower() == "true")
        if should_print_now:
            enqueue_qr_print(qr_path, reg_id)
        return f"/registrations/{reg_id}/{qr_filename}"
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")
        return None

def build_registration_enriched(payload: dict, data: dict, bcard_fields: dict) -> dict:
    return {
        "data": data,
        "bcard_fields": bcard_fields,
        "last_qr_raw": payload.get("last_qr_raw"),
        "last_mrz_text": payload.get("last_mrz_text"),
        "last_bcard_text": payload.get("last_bcard_text"),
        "ts": payload.get("ts") or int(time.time() * 1000),
        "bcard_name": bcard_fields.get("full_name") or bcard_fields.get("name"),
        "bcard_company": bcard_fields.get("company") or bcard_fields.get("org"),
        "bcard_email": bcard_fields.get("email"),
        "bcard_phone": bcard_fields.get("phone") or bcard_fields.get("tel"),
        "bcard_title": bcard_fields.get("title") or bcard_fields.get("position") or bcard_fields.get("role"),
        "bcard_address": bcard_fields.get("address"),
        "bcard_info": payload.get("last_bcard_text") or "",
    }


def is_registration_qr_scan(payload: dict, reg_id: str) -> bool:
    raw_qr = str(payload.get("last_qr_raw") or "").strip()
    reg_id = (reg_id or "").strip()
    if not raw_qr or not reg_id:
        return False
    text_match = re.search(r"(?mi)^ID:\s*(REG_[A-Za-z0-9_-]+)\s*$", raw_qr)
    if text_match:
        return text_match.group(1).strip() == reg_id
    if raw_qr != reg_id:
        try:
            parsed = json.loads(raw_qr)
        except Exception:
            return False
        qr_reg_id = str(parsed.get("registration_id") or parsed.get("r") or "").strip()
        qr_type = str(parsed.get("type") or parsed.get("t") or "").strip().lower()
        return qr_reg_id == reg_id and qr_type in {"registration_qr", "reg"}
    return bool(re.fullmatch(r"REG_[A-Za-z0-9_-]+", raw_qr))


def update_registration_json_with_ocr(reg_id: str, bcard_fields: dict, last_bcard_text: str = "") -> Optional[str]:
    reg_folder = REG_DIR / reg_id
    reg_folder.mkdir(exist_ok=True, parents=True)

    def updater(existing: dict) -> dict:
        existing_bcard_fields = existing.get("bcard_fields") or {}
        merged_fields = dict(existing_bcard_fields)
        for key, value in (bcard_fields or {}).items():
            if str(value or "").strip():
                merged_fields[key] = value
        return {
            **existing,
            "bcard_fields": merged_fields,
            "last_bcard_text": last_bcard_text if last_bcard_text else existing.get("last_bcard_text"),
            "bcard_name": merged_fields.get("full_name") or merged_fields.get("name"),
            "bcard_company": merged_fields.get("company") or merged_fields.get("org"),
            "bcard_email": merged_fields.get("email"),
            "bcard_phone": merged_fields.get("phone") or merged_fields.get("tel"),
            "bcard_title": merged_fields.get("title") or merged_fields.get("position") or merged_fields.get("role"),
            "bcard_address": merged_fields.get("address"),
            "bcard_info": last_bcard_text or existing.get("bcard_info") or existing.get("last_bcard_text") or "",
        }

    update_registration_json(reg_folder, updater)
    return generate_registration_qr(reg_folder, reg_id, submit_print=False)


def resolve_registration_display_name(data: dict, bcard_fields: Optional[dict]) -> str:
    src = bcard_fields or {}
    return (
        (src.get("full_name") or "").strip()
        or (src.get("name") or "").strip()
        or (data.get("fullName") or "").strip()
    )


def build_registration_greeting_text(name: str) -> str:
    clean_name = (name or "").strip()
    if not clean_name:
        return ""
    return f"Xin chao quy khach. Chao mung quay lai."


def generate_registration_greeting_audio(reg_id: str, display_name: str) -> Optional[str]:
    if not (reg_id or "").strip():
        return None
    return get_registration_greeting_audio_url(reg_id)


def save_registration(payload: dict) -> dict:
    logger.info("save_registration called with payload keys: %s", list(payload.keys()))
    t0 = time.time()
    data = payload.get("data", {}) or {}

    reg_id = payload.get("registration_id")
    logger.debug("save_registration: registrationId received='%s'", reg_id)
    if not reg_id:
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        reg_id = f"REG_{time.strftime('%d-%m-%Y_%H-%M-%S')}_{suffix}"

    reg_folder = REG_DIR / reg_id
    reg_folder.mkdir(exist_ok=True, parents=True)

    bcard_fields = (
        payload.get("bcard_fields")
        or payload.get("fields_ai")
        or payload.get("fields")
        or {}
    )
    has_bcard = has_meaningful_bcard_fields(bcard_fields)
    pending_bcard_ocr = bool(payload.get("pending_bcard_ocr")) and not has_bcard

    def updater(existing: dict) -> dict:
        existing_bcard_fields = existing.get("bcard_fields") or {}
        merged_bcard_fields = dict(existing_bcard_fields)
        for key, value in (bcard_fields or {}).items():
            if str(value or "").strip():
                merged_bcard_fields[key] = value

        existing_data = existing.get("data") or {}
        merged_data = dict(existing_data)
        for key, value in (data or {}).items():
            if str(value or "").strip():
                merged_data[key] = value

        base = build_registration_enriched(payload, merged_data, merged_bcard_fields)
        return {
            **existing,
            **base,
            "data": merged_data,
            "bcard_fields": merged_bcard_fields,
            "last_qr_raw": payload.get("last_qr_raw") or existing.get("last_qr_raw"),
            "last_mrz_text": payload.get("last_mrz_text") or existing.get("last_mrz_text"),
            "last_bcard_text": payload.get("last_bcard_text") or existing.get("last_bcard_text"),
            "ts": payload.get("ts") or existing.get("ts") or int(time.time() * 1000),
        }

    t_json0 = time.time()
    enriched = update_registration_json(reg_folder, updater)
    t_json = time.time() - t_json0

    saved = {"data": "data.json", "face": None, "bcard_image": None, "sources": []}

    # Save face image
    if payload.get("face_image"):
        saved["face"] = save_image_dataurl(reg_folder, "face", payload["face_image"])

    # Save business card image
    if isinstance(payload.get("bcard_image"), str) and "base64," in payload["bcard_image"]:
        saved["bcard_image"] = save_image_dataurl(reg_folder, "bcard", payload["bcard_image"], undistort=True)

    if has_bcard:
        append_checkin_line(reg_id, data, bcard_fields)

    # Business-card SQLite + QR
    qr_abs_url = None
    if has_bcard or pending_bcard_ocr:
        try:
            logger.info(
                "Saving business-card data to SQLite for reg_id=%s (has_bcard=%s, pending_bcard_ocr=%s)",
                reg_id,
                has_bcard,
                pending_bcard_ocr,
            )
            save_to_sqlite(reg_id, payload, data, bcard_fields, reg_folder)
            if is_registration_qr_scan(payload, reg_id):
                logger.info("Skipping QR regeneration for QR-scan check-in reg_id=%s", reg_id)
                if (reg_folder / "registration_qr.png").exists():
                    qr_abs_url = f"/registrations/{reg_id}/registration_qr.png"
            else:
                qr_abs_url = generate_registration_qr(reg_folder, reg_id, submit_print=True)
        except Exception as e:
            logger.error(f"Failed to save to SQLite: {e}", exc_info=True)
    else:
        logger.info("Skipping business-card SQLite insert for reg_id=%s because no business-card fields were provided", reg_id)

    greeting_audio_url = generate_registration_greeting_audio(
        reg_id,
        resolve_registration_display_name(data, bcard_fields),
    )
    t_json = time.time() - t_json0

    # Background cleanup
    try:
        threading.Thread(target=check_and_trigger_cleanup, args=(10000,), daemon=True).start()
    except Exception as cleanup_err:
        logger.error(f"Failed to start cleanup thread: {cleanup_err}")

    return {
        "ok": True,
        "registration_id": reg_id,
        "qr_url": qr_abs_url,
        "saved": saved,
        "greeting_audio_url": greeting_audio_url,
        "face_register_job_id": schedule_registration_face_embedding(reg_id, reg_folder) if saved.get("face") else None,
        "timing": {"json": round(t_json, 3)},
    }

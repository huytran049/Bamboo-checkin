import json
import random
import re
import shutil
import string
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps

from app_config import logger, REG_DIR, cv2, _HAS_CV2, _ensure_reader
from database.update_database import save_cccd_to_sqlite
from services.registration import save_image_dataurl, update_registration_json, generate_registration_qr
from services.face_service import schedule_registration_face_embedding


_CCCD_WORKER_PATH = (Path(__file__).resolve().parent.parent / "workers_swift" / "cccd_qr_ocr_worker.swift").resolve()


def _new_registration_id() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"REG_{time.strftime('%d-%m-%Y_%H-%M-%S')}_{suffix}"


def parse_vn_id_qr(raw: str) -> dict:
    parts = [str(part or "").strip() for part in str(raw or "").strip().split("|")]
    if len(parts) < 7:
        return {}
    id_number = "".join(ch for ch in parts[0] if ch.isdigit())
    if not (9 <= len(id_number) <= 12):
        return {}

    def to_iso(value: str) -> str:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) == 8:
            return f"{digits[4:8]}-{digits[2:4]}-{digits[0:2]}"
        return str(value or "").strip()

    gender = parts[4]
    if gender.lower() in {"m", "nam"}:
        gender = "Nam"
    elif gender.lower() in {"f", "nu", "nữ"}:
        gender = "Nữ"

    return {
        "idNumber": id_number,
        "oldId": parts[1],
        "fullName": parts[2],
        "dob": to_iso(parts[3]),
        "gender": gender,
        "address": parts[5],
        "expiry": to_iso(parts[6]),
    }


def _normalize_cccd_payload(data: Optional[dict]) -> dict:
    src = data or {}
    return {
        "idNumber": (src.get("idNumber") or src.get("id_number") or "").strip(),
        "oldId": (src.get("oldId") or src.get("old_id") or "").strip(),
        "fullName": (src.get("fullName") or src.get("full_name") or "").strip(),
        "dob": (src.get("dob") or "").strip(),
        "gender": (src.get("gender") or "").strip(),
        "address": (src.get("address") or "").strip(),
        "issued": (src.get("issued") or "").strip(),
        "expiry": (src.get("expiry") or "").strip(),
    }


def _detect_qr_with_cv(image_bytes: bytes) -> str:
    if not _HAS_CV2:
        return ""
    try:
        detector = cv2.QRCodeDetector()
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return ""
        decoded, _, _, = detector.detectAndDecodeMulti(frame)
        if isinstance(decoded, tuple) and len(decoded) >= 2:
            texts = decoded[1] or []
            for text in texts:
                if str(text or "").strip():
                    return str(text).strip()
        text, _, _ = detector.detectAndDecode(frame)
        return str(text or "").strip()
    except Exception:
        logger.exception("CCCD QR decode fallback failed")
        return ""


def _ocr_text_python(image_bytes: bytes) -> str:
    try:
        reader = _ensure_reader()
        if reader is None or getattr(reader, "engine", None) is None:
            return ""
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img).convert("RGB")
        texts = reader.readtext(np.array(img), detail=0)
        if isinstance(texts, list):
            return "\n".join(str(item).strip() for item in texts if str(item).strip())
    except Exception:
        logger.exception("CCCD OCR fallback failed")
    return ""


def _match_first(pattern: str, text: str) -> str:
    m = re.search(pattern, text or "", flags=re.I | re.S | re.M)
    return (m.group(1).strip() if m else "").strip()


def _parse_cccd_fields_from_ocr_text(ocr_text: str) -> dict:
    text = str(ocr_text or "").strip()
    if not text:
        return {}

    full_name = (
        _match_first(r"(?:full\s*name|ho,?\s*chu.*?ten\s*khai\s*sinh)\s*[:\-]?\s*\n\s*([^\n]+)", text)
        or _match_first(r"^([A-ZÀ-Ỹ][A-ZÀ-Ỹ\s]{5,})$", text)
    )
    dob = _match_first(r"(?:date\s*of\s*birth|ngay,?\s*thang,?\s*nam\s*sinh)\s*[:\-]?\s*\n?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", text)
    gender = _match_first(r"(?:gioi\s*tinh|sex)\s*[:\-]?\s*\n?\s*([^\n]+)", text)
    address = (
        _match_first(r"(?:place\s*of\s*residence|noi\s*thuong\s*tru)\s*[:\-]?\s*\n\s*([^\n]+(?:\n(?!ngay|gioi|sex|quoc\s*tich|nationality|co\s*gia\s*tri|date\s*of).+)*)", text)
        or _match_first(r"(?:place\s*of\s*residence|noi\s*thuong\s*tru)\s*[:\-]?\s*\n?\s*([^\n]+)", text)
    )

    normalized_gender = gender.strip()
    lower_gender = normalized_gender.lower()
    if "nam" in lower_gender or lower_gender in {"m", "male"}:
        normalized_gender = "Nam"
    elif "nữ" in lower_gender or "nu" in lower_gender or lower_gender in {"f", "female"}:
        normalized_gender = "Nữ"

    def to_iso(value: str) -> str:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) == 8:
            return f"{digits[4:8]}-{digits[2:4]}-{digits[0:2]}"
        return str(value or "").strip()

    return {
        "fullName": full_name.strip(),
        "dob": to_iso(dob) if dob else "",
        "gender": normalized_gender,
        "address": re.sub(r"\s*\n\s*", ", ", address).strip() if address else "",
    }


def _run_swift_cccd_worker(image_bytes: bytes) -> dict:
    swift_bin = shutil.which("swift")
    if not swift_bin or not _CCCD_WORKER_PATH.exists():
        return {}

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="cccd_", suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        proc = subprocess.run(
            [swift_bin, str(_CCCD_WORKER_PATH), tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        stdout = (proc.stdout or "").strip()
        if proc.returncode != 0 or not stdout:
            logger.warning("CCCD Swift worker failed: %s", (proc.stderr or stdout).strip())
            return {}
        return json.loads(stdout)
    except Exception:
        logger.exception("Failed to run CCCD Swift worker")
        return {}
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass


def run_cccd_qr_ocr_from_image_bytes(image_bytes: bytes) -> dict:
    result = _run_swift_cccd_worker(image_bytes)
    if result.get("ok"):
        result["data"] = _normalize_cccd_payload(result.get("data"))
        return result

    qr_raw = _detect_qr_with_cv(image_bytes)
    parsed = parse_vn_id_qr(qr_raw)
    ocr_text = _ocr_text_python(image_bytes)
    lower = ocr_text.lower()
    keywords = [
        token for token in (
            "can cuoc",
            "identity card",
            "citizen identity",
            "personal identification",
            "personal identification number",
            "full name",
            "date of birth",
            "sex",
            "ngay sinh",
            "gioi tinh",
            "noi thuong tru",
            "place of residence",
        )
        if token in lower
    ]
    data = _normalize_cccd_payload({**_parse_cccd_fields_from_ocr_text(ocr_text), **parsed})
    core_field_count = sum(
        1 for key in ("idNumber", "fullName", "dob", "gender", "address")
        if str(data.get(key) or "").strip()
    )
    has_core_identity = bool(str(data.get("idNumber") or "").strip() and str(data.get("fullName") or "").strip())
    is_cccd = bool(parsed) or len(keywords) >= 2 or (has_core_identity and core_field_count >= 4)
    return {
        "ok": True,
        "is_cccd": is_cccd,
        "qr": {"raw": qr_raw, "parsed": parsed},
        "ocr": {"text": ocr_text, "keywords": keywords},
        "data": data,
    }


def save_cccd_draft(payload: dict) -> dict:
    reg_id = str(payload.get("registration_id") or "").strip() or _new_registration_id()
    reg_folder = REG_DIR / reg_id
    reg_folder.mkdir(exist_ok=True, parents=True)

    cccd_data = _normalize_cccd_payload(payload.get("data"))

    saved = {"cccd_front": None, "cccd_back": None, "face": None}
    if isinstance(payload.get("image_data_url"), str) and "base64," in payload["image_data_url"]:
        side = "cccd_back" if str(payload.get("side") or "").strip().lower() == "back" else "cccd_front"
        saved[side] = save_image_dataurl(reg_folder, side, payload["image_data_url"], undistort=False)
    if isinstance(payload.get("cccd_front_image"), str) and "base64," in payload["cccd_front_image"]:
        saved["cccd_front"] = save_image_dataurl(reg_folder, "cccd_front", payload["cccd_front_image"], undistort=False)
    if isinstance(payload.get("cccd_back_image"), str) and "base64," in payload["cccd_back_image"]:
        saved["cccd_back"] = save_image_dataurl(reg_folder, "cccd_back", payload["cccd_back_image"], undistort=False)
    if isinstance(payload.get("face_image"), str) and "base64," in payload["face_image"]:
        saved["face"] = save_image_dataurl(reg_folder, "face", payload["face_image"], undistort=False)

    def updater(existing: dict) -> dict:
        merged_data = {
            **_normalize_cccd_payload(existing.get("data")),
            **{k: v for k, v in cccd_data.items() if v},
        }
        field_meta = payload.get("cccd_field_meta") or existing.get("cccd_field_meta") or {}
        qr_raw = str(payload.get("cccd_qr_raw") or payload.get("last_qr_raw") or existing.get("cccd_qr_raw") or "").strip()
        ocr_text = str(payload.get("cccd_ocr_text") or existing.get("cccd_ocr_text") or "").strip()
        return {
            **existing,
            "data": {**(existing.get("data") or {}), **merged_data},
            "cccd_scan_status": str(payload.get("cccd_scan_status") or existing.get("cccd_scan_status") or "draft"),
            "cccd_field_meta": field_meta,
            "cccd_qr_raw": qr_raw,
            "cccd_ocr_text": ocr_text,
            "last_qr_raw": qr_raw or existing.get("last_qr_raw"),
            "ts": payload.get("ts") or existing.get("ts") or int(time.time() * 1000),
        }

    enriched = update_registration_json(reg_folder, updater)
    merged_data = _normalize_cccd_payload(enriched.get("data"))
    qr_raw = str(enriched.get("cccd_qr_raw") or "").strip()
    ocr_text = str(enriched.get("cccd_ocr_text") or "").strip()
    scan_status = str(enriched.get("cccd_scan_status") or payload.get("cccd_scan_status") or "draft").strip().lower()

    qr_url = generate_registration_qr(
        reg_folder,
        reg_id,
        submit_print=(scan_status == "done"),
    )

    warnings: list[str] = []

    try:
        save_cccd_to_sqlite(
            reg_id,
            merged_data,
            qr_raw=qr_raw,
            ocr_text=ocr_text,
            reg_folder=reg_folder,
        )
    except Exception as exc:
        logger.exception("Failed to save CCCD draft to SQLite for %s", reg_id)
        warnings.append(f"sqlite_save_failed: {exc}")

    face_register_job_id = None
    if saved.get("face"):
        try:
            face_register_job_id = schedule_registration_face_embedding(reg_id, reg_folder)
        except Exception as exc:
            logger.exception("Failed to schedule face embedding for CCCD draft %s", reg_id)
            warnings.append(f"face_schedule_failed: {exc}")

    result = {
        "ok": True,
        "registration_id": reg_id,
        "saved": saved,
        "data": merged_data,
        "qr_url": qr_url,
        "face_register_job_id": face_register_job_id,
    }
    if warnings:
        result["warnings"] = warnings
    return result

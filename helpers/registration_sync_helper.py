import argparse
import json
import logging
from pathlib import Path
from typing import Optional

import qrcode

from qr_printing import enqueue_qr_print


logger = logging.getLogger("kiosk.registration_sync")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REG_DIR = PROJECT_ROOT / "registrations"


def _persist_registration_json(reg_folder: Path, enriched: dict) -> None:
    with (reg_folder / "data.json").open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)


def _generate_registration_qr(reg_folder: Path, reg_id: str, *, submit_print: bool = False) -> Optional[str]:
    reg_id = (reg_id or "").strip()
    if not reg_id:
        return None
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=2,
    )
    qr.add_data(reg_id)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_filename = "registration_qr.png"
    qr_path = reg_folder / qr_filename
    qr_img.save(str(qr_path))
    if submit_print:
        enqueue_qr_print(qr_path, reg_id)
    return f"/registrations/{reg_id}/{qr_filename}"


def update_registration_json_with_ocr(reg_id: str, bcard_fields: dict, last_bcard_text: str = "") -> dict:
    reg_folder = REG_DIR / reg_id
    reg_folder.mkdir(exist_ok=True, parents=True)
    data_path = reg_folder / "data.json"

    existing: dict = {}
    if data_path.exists():
        with data_path.open("r", encoding="utf-8") as f:
            existing = json.load(f) or {}

    existing_bcard_fields = existing.get("bcard_fields") or {}
    merged_fields = dict(existing_bcard_fields)
    for key, value in (bcard_fields or {}).items():
        if str(value or "").strip():
            merged_fields[key] = value

    enriched = {
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
    _persist_registration_json(reg_folder, enriched)
    qr_url = _generate_registration_qr(reg_folder, reg_id, submit_print=False)
    return {"ok": True, "registration_id": reg_id, "qr_url": qr_url, "bcard_fields": merged_fields}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", required=True)
    args = parser.parse_args()

    payload_path = Path(args.payload_file)
    with payload_path.open("r", encoding="utf-8") as f:
        payload = json.load(f) or {}

    reg_id = str(payload.get("reg_id") or "").strip()
    if not reg_id:
        raise ValueError("reg_id is required")

    fields = payload.get("fields") or {}
    text = str(payload.get("text") or "")
    result = update_registration_json_with_ocr(reg_id, fields, text)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

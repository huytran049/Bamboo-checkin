import argparse
import json
import os
import sys
from pathlib import Path

from database.update_database import (
    create_face_profile,
    get_face_db_stats,
    get_cccd_registration,
    get_registration,
    list_face_embeddings,
    mark_visitor_seen,
)
from face import extract_face_embedding, find_best_match
from services.registration_assets import (
    get_registration_greeting_audio_url,
)

LATEST_MATCH_SCORE_DELTA = float((os.getenv("FACE_LATEST_SCORE_DELTA") or "0.02").strip())


def _load_registration_metadata(registration_id: str) -> dict:
    registration_id = (registration_id or "").strip()
    if not registration_id:
        return {}

    try:
        bcard_record = get_registration(registration_id)
    except Exception:
        bcard_record = None
    if bcard_record:
        return {
            "display_name": (bcard_record.get("full_name") or "").strip(),
            "created_at": str(bcard_record.get("created_at") or "").strip(),
        }

    try:
        cccd_record = get_cccd_registration(registration_id)
    except Exception:
        cccd_record = None
    if cccd_record:
        return {
            "display_name": (cccd_record.get("full_name") or "").strip(),
            "created_at": str(cccd_record.get("created_at") or "").strip(),
        }

    data_path = Path("registrations") / registration_id / "data.json"
    if not data_path.exists():
        return {}
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    fields = payload.get("bcard_fields") or {}
    return {
        "display_name": (
            fields.get("full_name")
            or fields.get("name")
            or payload.get("data", {}).get("fullName")
            or ""
        ).strip(),
        "created_at": str(payload.get("created_at") or payload.get("ts") or "").strip(),
    }


def _resolve_display_name(registration_id: str) -> str:
    return (_load_registration_metadata(registration_id).get("display_name") or "").strip()


def _build_greeting_text(display_name: str) -> str:
    clean_name = (display_name or "").strip()
    if not clean_name:
        return ""
    return "Xin chao quy khach. Chao mung quay lai."


def _generate_greeting_audio(registration_id: str, display_name: str) -> str:
    if not (registration_id or "").strip():
        return ""
    return get_registration_greeting_audio_url(registration_id)


def _resolve_greeting_audio_url(registration_id: str, display_name: str = "") -> str:
    registration_id = (registration_id or "").strip()
    if not registration_id:
        return ""
    return _generate_greeting_audio(registration_id, display_name)


def _registration_created_at(registration_id: str) -> str:
    registration_id = (registration_id or "").strip()
    if not registration_id:
        return ""
    return str(_load_registration_metadata(registration_id).get("created_at") or "").strip()


def _pick_latest_candidate(top_matches: list[dict], score_delta: float) -> dict | None:
    if not top_matches:
        return None

    best = top_matches[0]
    best_score = float(best.get("score", 0.0))
    shortlisted: list[dict] = []

    for item in top_matches:
        score = float(item.get("score", 0.0))
        if best_score - score <= score_delta:
            enriched = dict(item)
            enriched["_registration_created_at"] = _registration_created_at(item.get("registration_id") or "")
            shortlisted.append(enriched)

    if not shortlisted:
        return best

    shortlisted.sort(
        key=lambda item: (
            item.get("_registration_created_at") or "",
            float(item.get("score", 0.0)),
        ),
        reverse=True,
    )
    chosen = dict(shortlisted[0])
    chosen.pop("_registration_created_at", None)
    return chosen


def register_face(registration_id: str, image_path: str) -> dict:
    if not registration_id:
        raise ValueError("registration_id is required for register")

    extracted = extract_face_embedding(image_path)
    profile = create_face_profile(
        registration_id,
        extracted["embedding"],
        quality_score=extracted.get("quality_score"),
        source_image=image_path,
        display_name=_resolve_display_name(registration_id),
    )
    visitor = profile["visitor"]
    return {
        "ok": True,
        "type": "register",
        "registration_id": registration_id,
        "visitor": visitor,
        "matched": False,
        "quality_score": extracted.get("quality_score"),
        "face_bbox": extracted.get("bbox"),
    }


def recognize_face(image_path: str, threshold: float) -> dict:
    extracted = extract_face_embedding(image_path)
    candidates = list_face_embeddings()
    match = find_best_match(extracted["embedding"], candidates, threshold=threshold)
    top_matches_raw = match.get("top_matches", [])
    best = match.get("best")
    if best and top_matches_raw:
        best = _pick_latest_candidate(top_matches_raw, LATEST_MATCH_SCORE_DELTA) or best
        match["best"] = best
        match["matched"] = bool(best and float(best.get("score", 0.0)) >= threshold)
    if best and match["matched"]:
        mark_visitor_seen(best["visitor_id"])

    visitor = None
    if best:
        resolved_name = (best.get("display_name") or "").strip()
        if not resolved_name:
            resolved_name = _resolve_display_name(best.get("registration_id") or "")
        visitor = {
            "id": int(best["visitor_id"]),
            "registration_id": best.get("registration_id"),
            "display_name": resolved_name,
            "last_seen_at": best.get("last_seen_at"),
            "greeting_audio_url": _resolve_greeting_audio_url(best.get("registration_id") or "", resolved_name),
        }

    top_matches = []
    for item in match.get("top_matches", []):
        resolved_name = (item.get("display_name") or "").strip()
        if not resolved_name:
            resolved_name = _resolve_display_name(item.get("registration_id") or "")
        top_matches.append(
            {
                "visitor_id": int(item["visitor_id"]),
                "registration_id": item.get("registration_id"),
                "display_name": resolved_name,
                "score": round(float(item.get("score", 0.0)), 6),
            }
        )

    return {
        "ok": True,
        "type": "recognize",
        "matched": bool(match["matched"]),
        "score": round(float(best.get("score", 0.0)), 6) if best else 0.0,
        "threshold": threshold,
        "visitor": visitor,
        "top_matches": top_matches,
        "quality_score": extracted.get("quality_score"),
        "face_bbox": extracted.get("bbox"),
        "db_stats": get_face_db_stats(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Face worker helper")
    parser.add_argument("--type", choices=["register", "recognize"], required=True)
    parser.add_argument("--image-path", required=True)
    parser.add_argument("--registration-id", default="")
    parser.add_argument("--threshold", type=float, default=0.40)
    args = parser.parse_args()

    try:
        if args.type == "register":
            result = register_face(args.registration_id, args.image_path)
        else:
            result = recognize_face(args.image_path, args.threshold)
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

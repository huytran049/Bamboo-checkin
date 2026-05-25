from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from io import BytesIO

from gtts import gTTS

from app_config import logger

QA_TTS_CACHE_TTL_SEC = max(60, int((os.getenv("QA_TTS_CACHE_TTL_SEC") or "3600").strip() or "3600"))
QA_TTS_SEGMENT_PAUSE_MS = max(0, int((os.getenv("QA_TTS_SEGMENT_PAUSE_MS") or "60").strip() or "60"))
QA_TTS_PLAYBACK_RATE = max(0.5, float((os.getenv("QA_TTS_PLAYBACK_RATE") or "1.15").strip() or "1.15"))
QA_TTS_GTTS_LANG = (os.getenv("QA_TTS_GTTS_LANG") or "vi").strip() or "vi"
QA_TTS_GTTS_TLD = (os.getenv("QA_TTS_GTTS_TLD") or "com").strip() or "com"

_QA_TTS_CACHE: dict[str, dict] = {}
_TTS_CACHE_LOCK = threading.Lock()


def _get_active_tts_lang() -> str:
    """Đọc ngôn ngữ TTS động — ưu tiên KIOSK_LANGUAGE, fallback về QA_TTS_GTTS_LANG."""
    kiosk_lang = (os.getenv("KIOSK_LANGUAGE") or "").strip().lower()
    if kiosk_lang in ("vi", "ja"):
        return kiosk_lang
    return (os.getenv("QA_TTS_GTTS_LANG") or "vi").strip() or "vi"


def _get_active_tts_tld(lang: str) -> str:
    """TLD phù hợp theo ngôn ngữ."""
    if lang == "ja":
        return "co.jp"
    return (os.getenv("QA_TTS_GTTS_TLD") or "com").strip() or "com"


def _prepare_tts_text(text: str) -> str:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        raise ValueError("Nội dung voice không được để trống")
    normalized = re.sub(r"\s*[\(\)\[\]\{\}]\s*", ", ", normalized)
    normalized = re.sub(r"\s+([,.!?])", r"\1", normalized)
    normalized = re.sub(r"([,.!?])(?=[^\s])", r"\1 ", normalized)
    normalized = re.sub(r",\s*,+", ", ", normalized)
    normalized = re.sub(r"\.\s*\.+", ". ", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized)
    return normalized.strip()


def _prune_tts_cache(now: float) -> None:
    expired_keys = [
        key
        for key, item in _QA_TTS_CACHE.items()
        if float(item.get("expires_at") or 0) <= now
    ]
    for key in expired_keys:
        _QA_TTS_CACHE.pop(key, None)


def _synthesize_gtts_mp3_bytes(text: str) -> bytes:
    lang = _get_active_tts_lang()
    tld = _get_active_tts_tld(lang)
    fp = BytesIO()
    gTTS(text=text, lang=lang, tld=tld, slow=False).write_to_fp(fp)
    return fp.getvalue()


def synthesize_answer_audio_bytes(text: str) -> bytes:
    lang = _get_active_tts_lang()
    tld = _get_active_tts_tld(lang)
    prepared_text = _prepare_tts_text(text)
    cache_key = hashlib.sha256(
        f"gtts|{lang}|{tld}|{prepared_text}".encode("utf-8")
    ).hexdigest()
    now = time.time()
    with _TTS_CACHE_LOCK:
        _prune_tts_cache(now)
        cached = _QA_TTS_CACHE.get(cache_key)
        if cached:
            return bytes(cached.get("audio") or b"")

    audio_bytes = _synthesize_gtts_mp3_bytes(prepared_text)
    with _TTS_CACHE_LOCK:
        _QA_TTS_CACHE[cache_key] = {
            "audio": audio_bytes,
            "expires_at": now + QA_TTS_CACHE_TTL_SEC,
        }
        _prune_tts_cache(time.time())
    return audio_bytes


def warmup_qa_tts() -> None:
    try:
        synthesize_answer_audio_bytes("Xin chào.")
    except Exception as exc:
        logger.warning("QA gTTS warmup skipped/failed: %s", exc)


def get_qa_tts_mime_type() -> str:
    return "audio/mpeg"


def get_qa_tts_status() -> dict:
    lang = _get_active_tts_lang()
    tld = _get_active_tts_tld(lang)
    return {
        "provider": "gtts",
        "active_voice": f"lang={lang}, tld={tld}",
        "language": lang,
        "segment_pause_ms": QA_TTS_SEGMENT_PAUSE_MS,
        "playback_rate": QA_TTS_PLAYBACK_RATE,
        "voices": [],
    }

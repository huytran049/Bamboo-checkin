from pathlib import Path


STATIC_SOUND_DIR = Path("static") / "sound"
STATIC_SOUND_DIR.mkdir(parents=True, exist_ok=True)

RETURNING_VISITOR_GREETING_FILENAME = "chaomungquaylai_vi.mp3"


def get_registration_greeting_audio_path(reg_id: str) -> Path:
    return STATIC_SOUND_DIR / RETURNING_VISITOR_GREETING_FILENAME


def get_registration_greeting_audio_url(reg_id: str) -> str:
    return f"/static/sound/{RETURNING_VISITOR_GREETING_FILENAME}"

import os
from pathlib import Path


ENV_FILE_PATH = Path(__file__).resolve().parent / ".env"


def _read_env_lines() -> list[str]:
    if not ENV_FILE_PATH.exists():
        return []
    return ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()


def _write_env_lines(lines: list[str]) -> None:
    content = "\n".join(lines)
    if content and not content.endswith("\n"):
        content += "\n"
    ENV_FILE_PATH.write_text(content, encoding="utf-8")


def get_dashboard_settings() -> dict:
    face_use_redis = (os.getenv("FACE_USE_REDIS", "0") or "0").strip()
    qr_print_enabled = (os.getenv("QR_PRINT_ENABLED", "false") or "false").strip().lower()
    appointment_overlay_enabled = (os.getenv("APPOINTMENT_OVERLAY_ENABLED", "false") or "false").strip().lower()
    kiosk_language = (os.getenv("KIOSK_LANGUAGE", "vi") or "vi").strip().lower()
    return {
        "face_recognition_enabled": face_use_redis != "1",
        "face_use_redis": face_use_redis,
        "qr_print_enabled": qr_print_enabled == "true",
        "qr_print_enabled_raw": qr_print_enabled,
        "appointment_overlay_enabled": appointment_overlay_enabled == "true",
        "appointment_overlay_enabled_raw": appointment_overlay_enabled,
        "kiosk_language": kiosk_language,
        "japanese_mode": kiosk_language == "ja",
    }


def get_kiosk_language() -> str:
    """Trả về ngôn ngữ hiện tại của kiosk: 'vi' hoặc 'ja'."""
    return (os.getenv("KIOSK_LANGUAGE", "vi") or "vi").strip().lower()


def update_env_values(updates: dict[str, str]) -> None:
    lines = _read_env_lines()
    remaining = {str(key): str(value) for key, value in (updates or {}).items()}
    updated_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue

        key, _ = line.split("=", 1)
        env_key = key.strip()
        if env_key in remaining:
            updated_lines.append(f"{env_key}={remaining.pop(env_key)}")
        else:
            updated_lines.append(line)

    for env_key, env_value in remaining.items():
        updated_lines.append(f"{env_key}={env_value}")

    _write_env_lines(updated_lines)

    for env_key, env_value in updates.items():
        os.environ[str(env_key)] = str(env_value)

    _sync_runtime_flags()


def _sync_runtime_flags() -> None:
    try:
        import app_config

        app_config._USE_REDIS_FACE = os.getenv("FACE_USE_REDIS", "0") == "1" and app_config._HAS_REDIS
    except Exception:
        pass

    try:
        import routes.face as face_routes

        face_routes._USE_REDIS_FACE = os.getenv("FACE_USE_REDIS", "0") == "1" and face_routes._HAS_REDIS
    except Exception:
        pass

    try:
        import services.face_service as face_service

        face_service._USE_REDIS_FACE = os.getenv("FACE_USE_REDIS", "0") == "1" and face_service._HAS_REDIS
    except Exception:
        pass

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    # Precedence: explicit path > ~/.config/dreams.env > project .env
    explicit = os.getenv("DREAMS_ENV_FILE", "").strip()
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.home() / ".config" / "dreams.env")
    candidates.append(Path.cwd() / ".env")

    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)


_load_env_files()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_model: str
    mongodb_uri: str
    mongodb_db: str
    default_timezone: str
    allowed_telegram_user_id: int | None
    allowed_chat_id: int | None


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: expected integer value.") from exc


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    return Settings(
        telegram_bot_token=token,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017").strip(),
        mongodb_db=os.getenv("MONGODB_DB", "dream_diary").strip(),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "UTC").strip(),
        allowed_telegram_user_id=_optional_int("ALLOWED_TELEGRAM_USER_ID"),
        allowed_chat_id=_optional_int("ALLOWED_CHAT_ID"),
    )

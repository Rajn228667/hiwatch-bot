import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = _ROOT / ".env"
    load_dotenv(env_path, encoding="utf-8-sig")
    load_dotenv(Path.cwd() / ".env", encoding="utf-8-sig")


_load_env()


def _clean(v: str | None) -> str:
    if not v:
        return ""
    return v.strip().strip('"').strip("'")


def _parse_ids(raw: str) -> list[int]:
    out: list[int] = []
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip()
        if p.lstrip("-").isdigit():
            out.append(int(p))
    return out


def _parse_usernames(raw: str) -> list[str]:
    out: list[str] = []
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip().lstrip("@").lower()
        if p:
            out.append(p)
    return out


class Settings:
    bot_token: str = _clean(os.getenv("BOT_TOKEN"))
    xai_api_key: str = _clean(os.getenv("XAI_API_KEY"))
    xai_model: str = _clean(os.getenv("XAI_MODEL")) or "grok-3-mini"
    xai_base_url: str = _clean(os.getenv("XAI_BASE_URL")) or "https://api.x.ai/v1"

    # Менеджеры: @STPierce и @Who_Knyaz
    admin_usernames: list[str] = _parse_usernames(
        _clean(os.getenv("ADMIN_USERNAMES"))
        or f"{_clean(os.getenv('ADMIN_USERNAME')) or 'STPierce'},Who_Knyaz"
    )
    admin_chat_ids_env: list[int] = _parse_ids(
        _clean(os.getenv("ADMIN_CHAT_IDS")) or _clean(os.getenv("ADMIN_CHAT_ID"))
    )

    # legacy single
    admin_username: str = (
        admin_usernames[0] if admin_usernames else "stpierce"
    )
    admin_chat_id: int | None = admin_chat_ids_env[0] if admin_chat_ids_env else None

    sticker_hello: str = _clean(os.getenv("STICKER_HELLO"))
    sticker_ok: str = _clean(os.getenv("STICKER_OK"))
    sticker_think: str = _clean(os.getenv("STICKER_THINK"))
    sticker_fire: str = _clean(os.getenv("STICKER_FIRE"))


settings = Settings()

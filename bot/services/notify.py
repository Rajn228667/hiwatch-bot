"""Доставка заявок менеджерам @STPierce и @Who_Knyaz (только ЛС менеджерам)."""

from __future__ import annotations

import logging
from html import escape

from bot.config import settings
from bot.storage import add_admin_id, get_admin_ids

log = logging.getLogger("pierce-bot.notify")


def manager_usernames() -> list[str]:
    return list(settings.admin_usernames or ["stpierce", "who_knyaz"])


def is_manager_username(username: str | None) -> bool:
    if not username:
        return False
    u = username.lower().lstrip("@")
    return u in {m.lower() for m in manager_usernames()}


def ensure_admin_from_user(user) -> bool:
    """Если пишет менеджер — сохранить его chat_id."""
    if not user:
        return False
    uname = getattr(user, "username", None) or ""
    if not is_manager_username(uname):
        return False
    uid = getattr(user, "id", None)
    if uid:
        add_admin_id(int(uid))
        log.info("Manager @%s bound id=%s", uname, uid)
        return True
    return False


def resolve_admin_ids() -> list[int]:
    """chat_id всех менеджеров: store + .env."""
    ids = list(get_admin_ids())
    for i in settings.admin_chat_ids_env:
        if i not in ids:
            ids.append(i)
    return ids


def resolve_admin_id() -> int | None:
    ids = resolve_admin_ids()
    return ids[0] if ids else None


# ── совместимость со старым кодом ──
def get_admin_id_compat():
    return resolve_admin_id()

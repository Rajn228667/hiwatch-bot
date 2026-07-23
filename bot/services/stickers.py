"""Optional stickers — never spam extra messages if stickers missing."""

from __future__ import annotations

from telegram import Message

from bot.config import settings


async def react(message: Message, mood: str = "ok") -> None:
    """Send sticker only when file_id configured. Silent otherwise (no emoji spam)."""
    sid = {
        "hello": settings.sticker_hello,
        "ok": settings.sticker_ok,
        "think": settings.sticker_think,
        "fire": settings.sticker_fire,
        "lead": settings.sticker_ok or settings.sticker_fire,
    }.get(mood, "")
    if not sid:
        return
    try:
        await message.reply_sticker(sid)
    except Exception:
        pass

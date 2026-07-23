from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu
from bot.services.ai import grok_reply
from bot.services.stickers import react
from bot.storage import push_history

router = Router(name="chat")


@router.callback_query(F.data == "ask:more")
async def ask_more(query: CallbackQuery) -> None:
    await query.message.answer("Слушаю 👂 Пиши вопрос по ПК / цене / камерам.", reply_markup=main_menu())
    await query.answer()


@router.callback_query(F.data == "info:prices")
async def info_prices(query: CallbackQuery) -> None:
    await query.message.answer(
        "💰 Настройка 5–15к · Сборка 8–15к · ПК+камеры 10–15к ₸",
        reply_markup=main_menu(),
    )
    await query.answer()


@router.message(F.text == "💬 Спросить Пирса")
async def ask_pierce(message: Message) -> None:
    await react(message, "think")
    await message.answer(
        "Я на линии. Кидай вопрос как человеку: что за ПК, что болит, какой бюджет.",
        reply_markup=main_menu(),
    )


@router.message(F.text)
async def free_chat(message: Message) -> None:
    """Catch-all AI chat (after specific handlers)."""
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # skip menu buttons handled elsewhere
    if text in {
        "📝 Оставить заявку",
        "💰 Цены",
        "🛠 Услуги",
        "📍 Офис",
        "💬 Спросить Пирса",
        "ℹ️ Помощь",
    }:
        return

    uid = message.from_user.id
    hist = push_history(uid, "user", text)
    # convert to role format without duplicating last user (already in hist)
    history = [{"role": h["role"], "content": h["content"]} for h in hist[:-1]]

    await message.bot.send_chat_action(message.chat.id, "typing")
    reply = await grok_reply(text, history=history)
    push_history(uid, "assistant", reply)
    await message.answer(reply, reply_markup=main_menu())

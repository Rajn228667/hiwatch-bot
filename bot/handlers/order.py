from __future__ import annotations

import re
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import get_settings
from bot.keyboards import after_lead, main_menu, order_services
from bot.services.stickers import react
from bot.states import OrderFSM
from bot.storage import get_admin_id, set_admin_id

router = Router(name="order")

SERVICE_MAP = {
    "setup": "Настройка ПК",
    "build": "Сборка / апгрейд",
    "surv": "ПК + видеонаблюдение",
    "other": "Другое / консультация",
}


def _user_tag(message: Message) -> str:
    u = message.from_user
    uname = f"@{u.username}" if u.username else "без username"
    return f"{u.full_name} ({uname}, id={u.id})"


@router.message(Command("order"))
@router.message(F.text == "📝 Оставить заявку")
async def order_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await react(message, "lead")
    await state.set_state(OrderFSM.name)
    await message.answer(
        "Ок, оформляем заявку 🔧\nКак тебя зовут?",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменил. Если что — снова «Оставить заявку».", reply_markup=main_menu())


@router.message(OrderFSM.name)
async def order_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Имя коротковато — напиши как к тебе обращаться.")
        return
    await state.update_data(name=name)
    await state.set_state(OrderFSM.phone)
    await message.answer("Телефон? (например +7 775 …)")


@router.message(OrderFSM.phone)
async def order_phone(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        await message.answer("Не похоже на телефон. Кинь номер целиком.")
        return
    await state.update_data(phone=raw)
    await state.set_state(OrderFSM.service)
    await message.answer("Какая услуга?", reply_markup=order_services())


@router.callback_query(F.data.startswith("svc:"))
async def order_service_cb(query: CallbackQuery, state: FSMContext) -> None:
    code = (query.data or "").split(":", 1)[-1]
    if code == "cancel":
        await state.clear()
        await query.message.answer("Ок, отменил.", reply_markup=main_menu())
        await query.answer()
        return
    svc = SERVICE_MAP.get(code, "Консультация")
    await state.update_data(service=svc)
    await state.set_state(OrderFSM.comment)
    await query.message.answer(
        f"Услуга: <b>{escape(svc)}</b>\nКоротко опиши задачу (ПК, сроки, бюджет…)",
        parse_mode="HTML",
    )
    await query.answer()


@router.message(OrderFSM.service)
async def order_service_text(message: Message, state: FSMContext) -> None:
    # if user typed instead of button
    await state.update_data(service=(message.text or "Консультация").strip())
    await state.set_state(OrderFSM.comment)
    await message.answer("Опиши задачу парой предложений.")


@router.message(OrderFSM.comment)
async def order_comment(message: Message, state: FSMContext) -> None:
    comment = (message.text or "").strip()
    if len(comment) < 3:
        await message.answer("Чуть подробнее, пожалуйста.")
        return
    data = await state.get_data()
    await state.clear()
    await react(message, "ok")

    lead = (
        "🆕 <b>ЗАЯВКА С БОТА</b>\n"
        f"👤 Клиент: {_user_tag(message)}\n"
        f"📝 Имя: {escape(data.get('name', '—'))}\n"
        f"📞 Тел: {escape(data.get('phone', '—'))}\n"
        f"🛠 Услуга: {escape(data.get('service', '—'))}\n"
        f"💬 Задача: {escape(comment)}\n"
    )

    # Confirm to client
    await message.answer(
        "✅ Заявка принята!\n"
        f"Имя: <b>{escape(data.get('name', ''))}</b>\n"
        f"Услуга: <b>{escape(data.get('service', ''))}</b>\n\n"
        "Оператор уже получил её. Ответ обычно 15–30 мин в рабочее время.",
        parse_mode="HTML",
        reply_markup=after_lead(),
    )

    # Forward to admin @STPierce (chat_id)
    admin_id = get_admin_id() or get_settings().admin_chat_id
    if admin_id:
        try:
            await message.bot.send_message(admin_id, lead, parse_mode="HTML")
            # also try to forward original for context
            try:
                await message.forward(admin_id)
            except Exception:
                pass
        except Exception as e:
            await message.answer(
                "Заявку сохранил у себя, но админ-чат пока не достучался. "
                f"Техничка: {type(e).__name__}"
            )
    else:
        await message.answer(
            "⚠️ Админ ещё не привязан. Пусть @STPierce напишет боту /setadmin"
        )

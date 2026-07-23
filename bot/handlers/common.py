from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import get_settings
from bot.keyboards import main_menu
from bot.services.stickers import react
from bot.storage import set_admin_id

router = Router(name="common")

PRICES = (
    "💰 <b>Прайс (ориентир)</b>\n\n"
    "• Базовая настройка — <b>от 5 000 ₸</b>\n"
    "• Полная настройка + ПО — <b>8–12 000 ₸</b>\n"
    "• ПК + видеонаблюдение — <b>10–15 000 ₸</b>\n"
    "• Сборка / апгрейд — <b>8–15 000 ₸</b>\n"
    "• Выезд — по согласованию\n\n"
    "Точную смету скажет оператор после короткой диагностики."
)

SERVICES = (
    "🛠 <b>Услуги Pierce Setting × HiWatch</b>\n\n"
    "1) Настройка ПК под ключ (ОС, драйверы, оптимизация)\n"
    "2) Сборка и апгрейд\n"
    "3) ПК + камеры: SADP, iVMS-4200, Hik-Connect\n"
    "4) Удалёнка / офис / выезд\n\n"
    "Офис: Шымкент, Тауке Хана 143."
)

HELP = (
    "ℹ️ <b>Как пользоваться ботом</b>\n\n"
    "• Пиши вопросы — отвечает AI-инженер «Пирс»\n"
    "• «Оставить заявку» — оформить заказ (уйдёт оператору)\n"
    "• Не нужно писать админу в личку — всё через бота\n"
    "• /order — быстрый старт заявки\n"
    "• /cancel — отменить сценарий"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    s = get_settings()
    # Register admin if username matches or /start admin
    uname = (message.from_user.username or "").lower()
    if uname == s.admin_username.lower() or (message.text or "").endswith("admin"):
        set_admin_id(message.chat.id)
        await message.answer(
            f"👑 Админ зарегистрирован.\nchat_id = <code>{message.chat.id}</code>\n"
            "Все заявки клиентов будут прилетать сюда.",
            parse_mode="HTML",
        )

    await react(message, "hello")
    name = message.from_user.first_name or "друг"
    await message.answer(
        f"Йо, {name}! Я <b>Пирс</b> ⚡\n"
        "Pierce Setting × HiWatch — настройка и сборка ПК, Шымкент.\n\n"
        "Кидай вопрос или жми <b>«Оставить заявку»</b> — "
        "оператор получит всё с твоим @username автоматически.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP, parse_mode="HTML", reply_markup=main_menu())


@router.message(F.text == "💰 Цены")
async def prices(message: Message) -> None:
    await react(message, "fire")
    await message.answer(PRICES, parse_mode="HTML")


@router.message(F.text == "🛠 Услуги")
async def services(message: Message) -> None:
    await message.answer(SERVICES, parse_mode="HTML")


@router.message(F.text == "📍 Офис")
async def office(message: Message) -> None:
    await message.answer(
        "📍 <b>Офис</b>\nШымкент, пр. Тауке Хана, 143\n"
        "Пн–Пт 10:00–19:00 · Сб 10:00–16:00\n"
        "На карте: Яндекс / 2ГИС — точка на сайте hikmart.",
        parse_mode="HTML",
    )


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(
        f"Твой chat_id: <code>{message.chat.id}</code>\n"
        f"username: @{message.from_user.username or '—'}",
        parse_mode="HTML",
    )


@router.message(Command("setadmin"))
async def set_admin_cmd(message: Message) -> None:
    """Only works if username matches ADMIN_USERNAME."""
    s = get_settings()
    uname = (message.from_user.username or "").lower()
    if uname != s.admin_username.lower():
        await message.answer("Недостаточно прав.")
        return
    set_admin_id(message.chat.id)
    await message.answer(f"✅ ADMIN_CHAT_ID = {message.chat.id}")

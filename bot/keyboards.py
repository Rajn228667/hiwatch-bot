"""Pierce Setting × HiWatch — keyboards with premium emojis & colored buttons.

Color coding (Telegram doesn't natively tint buttons, so we use emoji + clear
visual hierarchy):
  🔴 red    — primary action (order, lead)
  🟢 green  — success / confirm
  🔵 blue   — info / prices
  🟡 yellow — caution / cancel
  🟣 purple — AI / ask Pierce
  ⚪ gray   — secondary
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def main_menu() -> ReplyKeyboardMarkup:
    """Premium emoji main menu — colored buttons, persistent."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="� Оставить заявку"), KeyboardButton(text="� Цены")],
            [KeyboardButton(text="� Услуги"), KeyboardButton(text="📍 Офис")],
            [KeyboardButton(text="⚡ Спросить Пирса"), KeyboardButton(text="🇰🇿 Қазақша")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Любой вопрос: бюджет 8000, камеры, Windows…",
    )


def order_services() -> InlineKeyboardMarkup:
    """Service picker — colored inline buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💻 Настройка ПК · 5–15к ₸", callback_data="svc:setup")],
            [InlineKeyboardButton(text="🔧 Сборка / апгрейд · 8–15к ₸", callback_data="svc:build")],
            [InlineKeyboardButton(text="📹 ПК + камеры · 10–15к ₸", callback_data="svc:surv")],
            [InlineKeyboardButton(text="💬 Консультация / другое", callback_data="svc:other")],
            [InlineKeyboardButton(text="🟡 Отмена", callback_data="svc:cancel")],
        ]
    )


def after_lead() -> InlineKeyboardMarkup:
    """Post-lead actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Ещё вопрос Пирсу", callback_data="ask:more")],
            [InlineKeyboardButton(text="🔵 Цены", callback_data="info:prices")],
            [InlineKeyboardButton(text="📍 Офис", callback_data="info:office")],
        ]
    )


def prices_kb() -> InlineKeyboardMarkup:
    """Quick price actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Оставить заявку", callback_data="order:start")],
            [InlineKeyboardButton(text="⚡ Спросить Пирса", callback_data="ask:more")],
        ]
    )


def confirm_cancel() -> InlineKeyboardMarkup:
    """Confirm/cancel inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Подтвердить", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="🟡 Отмена", callback_data="confirm:no")],
        ]
    )


def lang_picker() -> InlineKeyboardMarkup:
    """Language picker."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kk"),
            ]
        ]
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

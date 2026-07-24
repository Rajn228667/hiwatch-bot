"""
HiWatch Settings Bot — быстрая минималистичная версия.
Поток: /start -> выбор категории -> имя -> телефон -> описание -> заказ админам.
Заказы -> @STPierce (1930108146) и @Who_Knyaz (1418146556).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─── ENV ─────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")

# Админы — ID и usernames
ADMIN_CHAT_IDS = [1930108146, 1418146556]  # @STPierce, @Who_Knyaz
ADMIN_USERNAMES = {"stpierce", "who_knyaz"}

# Сайт
HIKMART_API_URL = os.getenv("HIKMART_API_URL", "https://hikmart.vercel.app").rstrip("/")
HIKMART_BOT_TOKEN = os.getenv("HIKMART_BOT_TOKEN", "hikmart-bot-sync-2025")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

# ─── FSM ─────────────────────────────────────────────
USER_STATE: dict[int, dict] = {}


def _set_state(cid: int, step: str, **extra) -> None:
    s = USER_STATE.get(cid, {})
    s["step"] = step
    s.update(extra)
    USER_STATE[cid] = s


def _get_state(cid: int) -> dict:
    return USER_STATE.get(cid, {})


def _clear_state(cid: int) -> None:
    USER_STATE.pop(cid, None)


# ─── КЛАВИАТУРЫ ──────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["📝 Оставить заявку", "💰 Цены"],
        ["🛠 Услуги", "📍 Контакты"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def categories_kb() -> InlineKeyboardMarkup:
    """Категории услуг — выбор при заявке (без видеонаблюдения)."""
    kb = [
        [InlineKeyboardButton("💻 Настройка ПК", callback_data="cat:setup")],
        [InlineKeyboardButton("🔧 Сборка / апгрейд ПК", callback_data="cat:build")],
        [InlineKeyboardButton("🌐 Сетевое оборудование", callback_data="cat:net")],
        [InlineKeyboardButton("🔧 СКУД / Домофоны", callback_data="cat:access")],
        [InlineKeyboardButton("💬 Консультация / другое", callback_data="cat:other")],
        [InlineKeyboardButton("✕ Отмена", callback_data="cat:cancel")],
    ]
    return InlineKeyboardMarkup(kb)


def after_order_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("📝 Новая заявка", callback_data="order:start")],
        [InlineKeyboardButton("📍 Контакты", callback_data="info:contacts")],
    ]
    return InlineKeyboardMarkup(kb)


# ─── ТЕКСТЫ ──────────────────────────────────────────

WELCOME = (
    "👋 <b>Здравствуйте!</b>\n\n"
    "Я бот <b>HiWatch Settings</b> — настройка ПК, сборка "
    "и сетевое оборудование в Шымкенте.\n\n"
    "Выберите кнопку ниже 👇"
)

CATEGORY_LABELS = {
    "setup": "💻 Настройка ПК",
    "build": "🔧 Сборка / апгрейд ПК",
    "net": "🌐 Сетевое оборудование",
    "access": "🔧 СКУД / Домофоны",
    "other": "💬 Консультация / другое",
}

PRICES_TEXT = (
    "💰 <b>Цены и услуги</b>\n\n"
    "💻 <b>Настройка ПК</b> — от 8 000 до 20 000 ₸\n"
    "Windows 10/11, драйверы, программы, оптимизация\n\n"
    "🔧 <b>Сборка / апгрейд ПК</b> — от 12 000 до 30 000 ₸\n"
    "Подбор комплектующих, сборка, стресс-тест\n\n"
    "🌐 <b>Сетевое оборудование</b> — от 5 000 до 25 000 ₸\n"
    "Роутеры, коммутаторы, настройка Wi-Fi\n\n"
    "🔧 <b>СКУД / Домофоны</b> — от 10 000 до 30 000 ₸\n"
    "Установка, настройка, подключение\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🚚 Выезд по Шымкенту — <b>бесплатно</b>\n"
    "✅ Гарантия — <b>30 дней</b>"
)

SERVICES_TEXT = (
    "🛠 <b>Услуги</b>\n\n"
    "✅ Настройка ПК (Windows, Linux)\n"
    "✅ Установка драйверов и программ\n"
    "✅ Сборка ПК с нуля\n"
    "✅ Апгрейд ПК\n"
    "✅ Сетевое оборудование (роутеры, коммутаторы)\n"
    "✅ СКУД и домофоны\n"
    "✅ Удалённая помощь\n"
    "✅ Диагностика и ремонт\n\n"
    "📝 Нажмите «Оставить заявку»!"
)

OFFICE_TEXT = (
    "📍 <b>Контакты</b>\n\n"
    "📷 <b>Instagram:</b> @hiwatch.kz\n"
    "https://www.instagram.com/hiwatch.kz\n\n"
    "📞 <b>Менеджеры:</b>\n"
    "+7 708 001 12 12\n"
    "+7 777 187 17 17\n\n"
    "📍 <b>Адрес:</b> г. Шымкент, пр. Тауке хана, 143\n\n"
    "🕐 <b>Режим работы:</b>\n"
    "Пн–Сб: 10:00 – 20:00\n"
    "Воскресенье: выходной\n\n"
    "📝 Нажмите «Оставить заявку» — менеджер свяжется!"
)

HELP_TEXT = (
    "❓ <b>Помощь</b>\n\n"
    "📝 <b>Оставить заявку</b> — опишите проблему\n"
    "💰 <b>Цены</b> — прайс-лист\n"
    "🛠 <b>Услуги</b> — список услуг\n"
    "📍 <b>Контакты</b> — связь с нами\n\n"
    "Команды: /start, /order, /cancel"
)

ORDER_STEP_NAME = (
    "📝 <b>Заявка — шаг 1/3</b>\n\n"
    "Введите ваше <b>имя</b>:\n"
    "<i>(например: Алексей)</i>"
)

ORDER_STEP_PHONE = (
    "📞 <b>Заявка — шаг 2/3</b>\n\n"
    "Введите ваш <b>номер телефона</b>:\n"
    "<i>(например: +7 708 001 12 12)</i>"
)

ORDER_STEP_PROBLEM = (
    "💻 <b>Заявка — шаг 3/3</b>\n\n"
    "Опишите <b>проблему или задачу</b>:\n"
    "<i>(например: ПК тормозит, нужно переустановить Windows)</i>"
)

ORDER_DONE = (
    "✅ <b>Заявка принята!</b>\n\n"
    "Менеджер свяжется с вами в ближайшее время.\n"
    "🙏 Спасибо, что выбрали нас!"
)

ORDER_CANCELLED = "✕ Заявка отменена. Можно начать заново в любой момент."


# ─── УВЕДОМЛЕНИЯ АДМИНАМ ─────────────────────────────

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Отправить сообщение всем админам в ЛС."""
    for cid in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=cid, text=text, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            log.info(f"Admin {cid} notified")
        except Exception as e:
            log.warning(f"notify {cid}: {e}")


async def push_order_to_website(user, state: dict) -> None:
    """Пуш заказа на сайт -> /manager/orders."""
    try:
        payload = {
            "source": "telegram",
            "botName": "HiWatch_settings_bot",
            "customerName": state.get("name", "—"),
            "customerPhone": state.get("phone", "—"),
            "serviceType": state.get("service", "—"),
            "comment": state.get("problem", ""),
            "items": [
                {
                    "title": state.get("service", "Услуга HiWatch"),
                    "price": 0,
                    "quantity": 1,
                }
            ],
            "total": 0,
            "telegramUserId": str(user.id) if user else "",
            "telegramUsername": f"@{user.username}" if user and user.username else "",
        }
        url = f"{HIKMART_API_URL}/api/bot/order"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {HIKMART_BOT_TOKEN}",
        }
        data = json.dumps(payload).encode("utf-8")

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    log.info(f"Order pushed to site: {result.get('orderId')}")
                else:
                    log.warning(f"Site API returned {resp.status}")
    except Exception as e:
        log.warning(f"push_order_to_website: {e}")


def _now_str() -> str:
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=6))
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")


def _build_order_message(user, state: dict) -> str:
    name = state.get("name", "—")
    phone = state.get("phone", "—")
    service = state.get("service", "—")
    problem = state.get("problem", "—")
    un = f"@{user.username}" if user.username else "нет"
    full = (user.full_name or "—").strip()
    uid = user.id

    return (
        "📝 <b>НОВАЯ ЗАЯВКА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"🛠 <b>Услуга:</b> {service}\n"
        f"💻 <b>Описание:</b> {problem}\n\n"
        f"💬 <b>Telegram:</b> {un}\n"
        f"🏷 <b>Имя в TG:</b> {full}\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n\n"
        f"🕐 <b>Время:</b> {_now_str()}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


# ─── ХЕНДЛЕРЫ ────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and user.username and user.username.lower() in ADMIN_USERNAMES:
        cid = user.id
        if cid not in ADMIN_CHAT_IDS:
            ADMIN_CHAT_IDS.append(cid)
            log.info(f"Admin bound: @{user.username} -> {cid}")

    if user:
        _clear_state(user.id)

    await update.message.reply_text(
        WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
    )


async def cmd_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    _set_state(user.id, "cat")
    await update.message.reply_text(
        "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
        parse_mode=ParseMode.HTML,
        reply_markup=categories_kb(),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        _clear_state(user.id)
    await update.message.reply_text(
        ORDER_CANCELLED, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await update.message.reply_text(
            f"🆔 Ваш chat_id: <code>{user.id}</code>",
            parse_mode=ParseMode.HTML,
        )


# ─── CALLBACK ────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = query.from_user
    if not user:
        return
    data = query.data or ""
    uid = user.id

    # Выбор категории
    if data.startswith("cat:"):
        action = data.split(":", 1)[1]
        if action == "cancel":
            _clear_state(uid)
            await query.edit_message_text(ORDER_CANCELLED, parse_mode=ParseMode.HTML)
            await context.bot.send_message(
                chat_id=uid, text=WELCOME, parse_mode=ParseMode.HTML,
                reply_markup=main_menu_kb()
            )
            return
        label = CATEGORY_LABELS.get(action, "💬 Консультация")
        _set_state(uid, "name", service=label)
        await query.edit_message_text(ORDER_STEP_NAME, parse_mode=ParseMode.HTML)
        return

    # Новая заявка
    if data == "order:start":
        _set_state(uid, "cat")
        await query.edit_message_text(
            "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
            parse_mode=ParseMode.HTML, reply_markup=categories_kb(),
        )
        return

    # Контакты
    if data == "info:contacts":
        await query.edit_message_text(OFFICE_TEXT, parse_mode=ParseMode.HTML)
        return


# ─── ТЕКСТОВЫЕ СООБЩЕНИЯ ─────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    text = (update.message.text or "").strip()
    state = _get_state(user.id)
    step = state.get("step", "")

    # Отмена
    if "Отмена" in text or text == "✕ Отмена":
        _clear_state(user.id)
        await update.message.reply_text(
            ORDER_CANCELLED, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
        )
        return

    # Кнопки меню
    if "Оставить заявку" in text:
        _set_state(user.id, "cat")
        await update.message.reply_text(
            "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
            parse_mode=ParseMode.HTML, reply_markup=categories_kb(),
        )
        return

    if "Цены" in text:
        await update.message.reply_text(PRICES_TEXT, parse_mode=ParseMode.HTML)
        return

    if "Услуги" in text and "Контакты" not in text:
        await update.message.reply_text(SERVICES_TEXT, parse_mode=ParseMode.HTML)
        return

    if "Контакты" in text or "контакты" in text:
        await update.message.reply_text(OFFICE_TEXT, parse_mode=ParseMode.HTML)
        return

    # FSM — шаг 1: имя
    if step == "name":
        if len(text) < 2:
            await update.message.reply_text("❌ Имя слишком короткое. Введите ещё раз:")
            return
        _set_state(user.id, "phone", name=text, service=state.get("service", "—"))
        await update.message.reply_text(ORDER_STEP_PHONE, parse_mode=ParseMode.HTML)
        return

    # FSM — шаг 2: телефон
    if step == "phone":
        digits = "".join(c for c in text if c.isdigit())
        if len(digits) < 7:
            await update.message.reply_text(
                "❌ Неверный номер. Введите ещё раз:\n<i>(например: +7 708 001 12 12)</i>",
                parse_mode=ParseMode.HTML,
            )
            return
        _set_state(user.id, "problem",
                   name=state.get("name", ""), phone=text,
                   service=state.get("service", "—"))
        await update.message.reply_text(ORDER_STEP_PROBLEM, parse_mode=ParseMode.HTML)
        return

    # FSM — шаг 3: описание проблемы
    if step == "problem":
        if len(text) < 3:
            await update.message.reply_text("❌ Опишите подробнее (минимум 3 символа):")
            return
        state["problem"] = text
        order_msg = _build_order_message(user, state)
        # Отправка админам
        await notify_admins(context, order_msg)
        # Пуш на сайт
        await push_order_to_website(user, state)
        # Подтверждение пользователю
        await update.message.reply_text(
            ORDER_DONE, parse_mode=ParseMode.HTML, reply_markup=after_order_kb()
        )
        _clear_state(user.id)
        return

    # Неизвестный текст -> меню
    await update.message.reply_text(
        "Используйте кнопки меню 👇",
        reply_markup=main_menu_kb(),
    )


# ─── ОБРАБОТКА ОШИБОК ────────────────────────────────

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error(f"Error: {context.error}")


# ─── MAIN ────────────────────────────────────────────

def build_application() -> Application:
    """Создание Application — используется в bot.py и wsgi.py."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден в .env!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .read_timeout(10)
        .write_timeout(10)
        .connect_timeout(5)
        .pool_timeout(5)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("order", cmd_order))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("help", cmd_start))

    # Callback
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Ошибки
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в .env!")
        return

    app = build_application()

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if webhook_url:
        port = int(os.getenv("PORT", "10000"))
        print(f"🤖 Бот запущен (webhook) -> {webhook_url}/{BOT_TOKEN}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{webhook_url}/{BOT_TOKEN}",
        )
    else:
        print("🤖 Бот запущен (polling)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

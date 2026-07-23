"""
HiWatch Settings Bot — профессиональная минималистичная версия.
Без цветных кружков/квадратов. Анимированные Telegram эмодзи.
Быстрый, лёгкий, асинхронный.
Заказы → @STPierce и @Who_Knyaz.
"""
from __future__ import annotations

import asyncio
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
load_dotenv(Path.cwd() / ".env", encoding="utf-8-sig")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
ADMIN_USERNAMES = [
    u.strip().lstrip("@").lower()
    for u in (os.getenv("ADMIN_USERNAMES") or "STPierce,Who_Knyaz").replace(";", ",").split(",")
    if u.strip()
]
ADMIN_CHAT_IDS: list[int] = []
_raw_ids = os.getenv("ADMIN_CHAT_IDS") or os.getenv("ADMIN_CHAT_ID") or ""
for _id in _raw_ids.replace(";", ",").split(","):
    _id = _id.strip()
    if _id.lstrip("-").isdigit():
        ADMIN_CHAT_IDS.append(int(_id))

# ─── HIKMART WEBSITE INTEGRATION ─────────────────────
# Orders from the bot are pushed to the Hikmart website API,
# so they appear in the manager panel (/manager/orders) alongside website orders.
HIKMART_API_URL = os.getenv("HIKMART_API_URL", "https://hikmart.kz").rstrip("/")
HIKMART_BOT_TOKEN = os.getenv("HIKMART_BOT_TOKEN", "hikmart-bot-sync-2025")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
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


# ─── KEYBOARDS ───────────────────────────────────────
# Минимализм: чистые текстовые кнопки + анимированные эмодзи

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = [
        ["📝 Оставить заявку", "💰 Цены"],
        ["🛠 Услуги", "📍 Контакты"],
        ["❓ Помощь"],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)


def services_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("💻 Настройка ПК · от 8 000 ₸", callback_data="svc:setup")],
        [InlineKeyboardButton("🔧 Сборка / апгрейд · от 12 000 ₸", callback_data="svc:build")],
        [InlineKeyboardButton("📹 Видеонаблюдение · от 15 000 ₸", callback_data="svc:surv")],
        [InlineKeyboardButton("💬 Консультация / другое", callback_data="svc:other")],
        [InlineKeyboardButton("✕ Отмена", callback_data="svc:cancel")],
    ]
    return InlineKeyboardMarkup(kb)


def after_order_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("📝 Новая заявка", callback_data="order:start")],
        [InlineKeyboardButton("💰 Цены", callback_data="info:prices")],
        [InlineKeyboardButton("📍 Контакты", callback_data="info:contacts")],
    ]
    return InlineKeyboardMarkup(kb)


# ─── MESSAGES ────────────────────────────────────────

WELCOME = (
    "👋 <b>Здравствуйте!</b>\n\n"
    "Я бот <b>HiWatch Settings</b> — настройка ПК, сборка и видеонаблюдение в Шымкенте.\n\n"
    "Что я умею:\n"
    "📝 — оставить заявку (менеджер свяжется с вами)\n"
    "💰 — цены и услуги\n"
    "🛠 — список всех услуг\n"
    "📍 — офис и контакты\n\n"
    "Нажмите кнопку ниже 👇"
)

PRICES_TEXT = (
    "💰 <b>Цены и услуги</b>\n\n"
    "💻 <b>Настройка ПК</b> — от 8 000 до 20 000 ₸\n"
    "Установка Windows 10/11, драйверов, программ, оптимизация, антивирус\n\n"
    "🔧 <b>Сборка / апгрейд ПК</b> — от 12 000 до 30 000 ₸\n"
    "Подбор комплектующих, сборка с MX-6, стресс-тест, отчёт\n\n"
    "📹 <b>ПК + видеонаблюдение</b> — от 15 000 до 35 000 ₸\n"
    "Hikvision, HiWatch: SADP, iVMS-4200, Hik-Connect, архив, удалённый доступ\n\n"
    "💬 <b>Консультация</b> — бесплатно\n"
    "Помощь с выбором, диагностика проблемы\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🚚 Выезд по Шымкенту — <b>бесплатно</b>\n"
    "✅ Гарантия на все работы — <b>30 дней</b>"
)

SERVICES_TEXT = (
    "🛠 <b>Услуги</b>\n\n"
    "✅ Настройка ПК (Windows 10/11, Linux)\n"
    "✅ Установка драйверов и программ\n"
    "✅ Сборка ПК с нуля\n"
    "✅ Апгрейд существующего ПК\n"
    "✅ Настройка видеонаблюдения (Hikvision, HiWatch, Dahua)\n"
    "✓ SADP, iVMS-4200, Hik-Connect\n"
    "✓ Архив, права доступа, уведомления\n"
    "✅ Удалённая помощь\n"
    "✅ Диагностика и ремонт\n"
    "✅ Консультации по подбору техники\n\n"
    "📝 Нажмите «Оставить заявку» — менеджер свяжется!"
)

OFFICE_TEXT = (
    "📍 <b>Офис и контакты</b>\n\n"
    "🏢 <b>Адрес:</b> Шымкент, пр. Тауке Хана, 143\n"
    "📞 <b>Телефон:</b> +7 (708) 001-12-12\n"
    "🌐 <b>Сайт:</b> hikmart.kz\n"
    "📷 <b>Instagram:</b> @hikmart.kz\n\n"
    "🕐 <b>Режим работы:</b>\n"
    "Пн–Сб: 10:00 – 20:00\n"
    "Воскресенье: выходной"
)

HELP_TEXT = (
    "❓ <b>Помощь</b>\n\n"
    "📝 <b>Оставить заявку</b> — опишите проблему, менеджер свяжется\n"
    "💰 <b>Цены</b> — прайс-лист на все услуги\n"
    "🛠 <b>Услуги</b> — полный список услуг\n"
    "📍 <b>Контакты</b> — адрес, телефон, режим работы\n\n"
    "Команды: /start, /order, /help, /cancel"
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
    "Обсудим цену, адрес и удобное время.\n\n"
    "🙏 Спасибо, что выбрали нас!"
)

ORDER_CANCELLED = "✕ Заявка отменена. Можно начать заново в любой момент."

SERVICE_LABELS = {
    "setup": "💻 Настройка ПК",
    "build": "🔧 Сборка / апгрейд",
    "surv": "📹 Видеонаблюдение",
    "other": "💬 Консультация",
}


# ─── ADMIN NOTIFICATION ──────────────────────────────

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    for cid in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=cid, text=text, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            log.warning(f"notify {cid}: {e}")


async def push_order_to_website(user, state: dict) -> None:
    """Push the completed order to the Hikmart website API.

    The order will appear in the manager panel (/manager/orders) with
    source="telegram", alongside orders placed through the website.
    Uses aiohttp if available, falls back to urllib.
    """
    try:
        import json as _json
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
        data = _json.dumps(payload).encode("utf-8")

        try:
            import aiohttp  # type: ignore
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        log.info(f"Order pushed to Hikmart: {result.get('orderId')}")
                    else:
                        log.warning(f"Hikmart API returned {resp.status}")
        except ImportError:
            # Fallback: urllib (sync, but quick)
            import urllib.request
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        log.info("Order pushed to Hikmart (urllib)")
                    else:
                        log.warning(f"Hikmart API returned {resp.status}")
            except Exception as e:
                log.warning(f"Hikmart urllib push failed: {e}")
    except Exception as e:
        log.warning(f"push_order_to_website error: {e}")


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


def _now_str() -> str:
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=6))
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")


# ─── ANIMATED EMOJI ──────────────────────────────────
# Telegram animated emojis (dice, slot, darts, etc.)
# Sent via sendDice for premium feel

async def send_welcome_animation(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send a subtle animated emoji on /start."""
    try:
        await context.bot.send_dice(chat_id=chat_id, emoji="👋")
    except Exception:
        pass  # Not critical


# ─── HANDLERS ────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user and user.username and user.username.lower() in ADMIN_USERNAMES:
        cid = user.id
        if cid not in ADMIN_CHAT_IDS:
            ADMIN_CHAT_IDS.append(cid)
            log.warning(f"Admin bound: @{user.username} → {cid}")

    _clear_state(user.id if user else 0)

    # Send animated emoji first (fast, premium feel)
    await send_welcome_animation(context, update.effective_chat.id)

    await update.message.reply_text(
        WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
    )


async def cmd_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    _set_state(user.id, "svc")
    await update.message.reply_text(
        "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
        parse_mode=ParseMode.HTML,
        reply_markup=services_kb(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await update.message.reply_text(
            f"🆔 Ваш chat_id: <code>{user.id}</code>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    is_admin = (user.username and user.username.lower() in ADMIN_USERNAMES)
    if not is_admin:
        await update.message.reply_text("⛔ Эта команда только для менеджеров.")
        return
    cid = user.id
    if cid not in ADMIN_CHAT_IDS:
        ADMIN_CHAT_IDS.append(cid)
    await update.message.reply_text(
        f"✅ Вы привязаны как менеджер.\n🆔 <code>chat_id: {cid}</code>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        _clear_state(user.id)
    await update.message.reply_text(
        ORDER_CANCELLED, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
    )


# ─── CALLBACK QUERY ──────────────────────────────────

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

    if data.startswith("svc:"):
        action = data.split(":", 1)[1]
        if action == "cancel":
            _clear_state(uid)
            await query.edit_message_text(ORDER_CANCELLED, parse_mode=ParseMode.HTML)
            await context.bot.send_message(
                chat_id=uid, text=WELCOME, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
            )
            return
        label = SERVICE_LABELS.get(action, "💬 Консультация")
        _set_state(uid, "name", service=label)
        await query.edit_message_text(ORDER_STEP_NAME, parse_mode=ParseMode.HTML)
        return

    if data == "order:start":
        _set_state(uid, "svc")
        await query.edit_message_text(
            "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
            parse_mode=ParseMode.HTML, reply_markup=services_kb(),
        )
        return

    if data == "info:prices":
        await query.edit_message_text(PRICES_TEXT, parse_mode=ParseMode.HTML)
        return

    if data == "info:contacts":
        await query.edit_message_text(OFFICE_TEXT, parse_mode=ParseMode.HTML)
        return


# ─── TEXT MESSAGE HANDLER ────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    text = (update.message.text or "").strip()
    state = _get_state(user.id)
    step = state.get("step", "")

    # Cancel
    if "Отмена" in text or text == "✕ Отмена":
        _clear_state(user.id)
        await update.message.reply_text(
            ORDER_CANCELLED, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb()
        )
        return

    # Menu buttons — check first for fast response
    if "Оставить заявку" in text:
        _set_state(user.id, "svc")
        await update.message.reply_text(
            "📝 <b>Заявка</b>\n\nВыберите нужную услугу:",
            parse_mode=ParseMode.HTML, reply_markup=services_kb(),
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

    if "Помощь" in text or "помощь" in text:
        await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)
        return

    # FSM steps
    if step == "name":
        if len(text) < 2:
            await update.message.reply_text("❌ Имя слишком короткое. Введите ещё раз:")
            return
        _set_state(user.id, "phone", name=text, service=state.get("service", "—"))
        await update.message.reply_text(ORDER_STEP_PHONE, parse_mode=ParseMode.HTML)
        return

    if step == "phone":
        digits = "".join(c for c in text if c.isdigit())
        if len(digits) < 7:
            await update.message.reply_text(
                "❌ Неверный номер. Введите ещё раз:\n<i>(например: +7 708 001 12 12)</i>",
                parse_mode=ParseMode.HTML,
            )
            return
        _set_state(user.id, "problem",
                   name=state.get("name", ""), phone=text, service=state.get("service", "—"))
        await update.message.reply_text(ORDER_STEP_PROBLEM, parse_mode=ParseMode.HTML)
        return

    if step == "problem":
        if len(text) < 3:
            await update.message.reply_text("❌ Опишите подробнее (минимум 3 символа):")
            return
        state["problem"] = text
        order_msg = _build_order_message(user, state)
        await notify_admins(context, order_msg)
        # Push order to Hikmart website (manager panel)
        await push_order_to_website(user, state)
        await update.message.reply_text(
            ORDER_DONE, parse_mode=ParseMode.HTML, reply_markup=after_order_kb()
        )
        _clear_state(user.id)
        return

    # Unknown text → show menu
    await update.message.reply_text(
        "Используйте кнопки меню 👇",
        reply_markup=main_menu_kb(),
    )


# ─── ERROR HANDLER ───────────────────────────────────

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error(f"Error: {context.error}")


# ─── MAIN ────────────────────────────────────────────

def build_application() -> Application:
    """Build the Telegram bot Application with all handlers.
    Shared between polling mode (bot.py main) and WSGI mode (wsgi.py for PythonAnywhere).
    """
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден в .env!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)  # Process updates concurrently
        .read_timeout(10)
        .write_timeout(10)
        .connect_timeout(5)
        .pool_timeout(5)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("order", cmd_order))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("setadmin", cmd_setadmin))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Callback queries
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Errors
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в .env!")
        print("Создайте .env файл: BOT_TOKEN=ваш_токен")
        return

    app = build_application()

    # Webhook or polling
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if webhook_url:
        port = int(os.getenv("PORT", "10000"))
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

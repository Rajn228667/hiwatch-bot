"""
Pierce Setting × HiWatch — Telegram bot (PTB 21 + Grok).

  cd telegram-bot   (или Desktop\\HiWatch_settings_bot)
  python -m venv .venv
  .venv\\Scripts\\activate
  pip install -r requirements.txt
  # .env: BOT_TOKEN=...  XAI_API_KEY=...
  python -m bot.main

Admin @STPierce: /setadmin
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from html import escape
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import settings
from bot.services.ai import grok_reply
from bot.services.notify import (
    ensure_admin_from_user,
    notify_admin,
    notify_lead,
    notify_user_message,
    resolve_admin_id,
)
from bot.services.stickers import react
from bot.storage import get_admin_id, push_history, set_admin_id

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("pierce-bot")

NAME, PHONE, SERVICE, COMMENT = range(4)

SERVICE_MAP = {
    "setup": "Настройка ПК / ПК баптау",
    "build": "Сборка / апгрейд / Жинау",
    "surv": "ПК + видеонаблюдение / бейнебақылау",
    "other": "Другое / Басқа",
}


def menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📝 Оставить заявку", "💰 Цены"],
            ["🛠 Услуги", "📍 Офис"],
            ["💬 Спросить Пирса", "🇰🇿 Қазақша"],
            ["ℹ️ Помощь"],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Любой вопрос: бюджет 8000, камеры, Windows…",
    )


def svc_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Настройка ПК (5–15к)", callback_data="svc:setup")],
            [InlineKeyboardButton("Сборка / апгрейд (8–15к)", callback_data="svc:build")],
            [InlineKeyboardButton("ПК + камеры (10–15к)", callback_data="svc:surv")],
            [InlineKeyboardButton("Другое / Басқа", callback_data="svc:other")],
            [InlineKeyboardButton("❌ Отмена", callback_data="svc:cancel")],
        ]
    )


def user_tag(update: Update) -> str:
    u = update.effective_user
    uname = f"@{u.username}" if u and u.username else "без username"
    name = u.full_name if u else "?"
    uid = u.id if u else 0
    return f"{name} ({uname}, id={uid})"


def _lang(update: Update) -> str:
    code = (update.effective_user.language_code or "ru").lower()
    if code.startswith("kk") or code.startswith("kz"):
        return "kk"
    if code.startswith("en"):
        return "en"
    return "ru"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    u = update.effective_user
    log.info("/start from %s", user_tag(update))
    try:
        # Автопривязка @STPierce → заявки в его ЛС
        if ensure_admin_from_user(u) or (
            u and (u.username or "").lower().lstrip("@") == settings.admin_username.lower()
        ):
            set_admin_id(update.effective_chat.id)
            await update.message.reply_text(
                f"👑 Админ @{settings.admin_username} привязан.\n"
                f"chat_id={update.effective_chat.id}\n"
                "Заявки клиентов будут приходить сюда в ЛС.",
                reply_markup=menu(),
            )

        await react(update.message, "hello")
        name = (u.first_name if u else "друг") or "друг"
        lang = _lang(update)
        if lang == "kk":
            text = (
                f"Сәлем, {name}! Мен Пирс ⚡\n"
                "Pierce Setting × HiWatch — ПК баптау/жинау, Шымкент.\n\n"
                "Сұрағыңды жаз немесе «📝 Оставить заявку» бас.\n"
                "Әкімшіге жеке жазу қажет емес — бәрі бот арқылы."
            )
        else:
            text = (
                f"Йо, {name}! Я Пирс ⚡\n"
                "Pierce Setting × HiWatch — настройка/сборка ПК, Шымкент.\n\n"
                "Пиши любой вопрос (например: бюджет 8000) или жми «Оставить заявку».\n"
                "В личку админу писать не нужно — всё через бота.\n"
                "Қазақша жазсаң — қазақша жауап беремін 🇰🇿"
            )
        await update.message.reply_text(text, reply_markup=menu())
        log.info("/start ok → %s", u.id if u else "?")
    except Exception as e:
        log.exception("/start failed: %s", e)
        try:
            await update.message.reply_text(
                "Привет! Я Пирс. Напиши вопрос или нажми «Оставить заявку».",
                reply_markup=menu(),
            )
        except Exception:
            pass


async def cmd_setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    uname = (update.effective_user.username or "").lower().lstrip("@")
    if uname != settings.admin_username.lower():
        await update.message.reply_text(
            f"Недостаточно прав. Нужен аккаунт @{settings.admin_username}."
        )
        return
    set_admin_id(update.effective_chat.id)
    ok = await notify_admin(
        context,
        f"✅ Админ ЛС активен\n"
        f"@{settings.admin_username}\n"
        f"chat_id=<code>{update.effective_chat.id}</code>\n"
        "Сюда будут приходить заявки и сообщения клиентов.",
    )
    await update.message.reply_text(
        f"✅ ADMIN = <code>{update.effective_chat.id}</code>\n"
        + ("Тестовое сообщение отправлено в эту ЛС." if ok else "Не удалось отправить тест."),
        parse_mode=ParseMode.HTML,
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    u = update.effective_user
    await update.message.reply_text(
        f"chat_id: <code>{update.effective_chat.id}</code>\n"
        f"username: @{u.username or '—'}",
        parse_mode=ParseMode.HTML,
    )


async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await react(update.message, "fire")
    await update.message.reply_text(
        "💰 <b>Прайс / Баға</b>\n"
        "• Базовая / Негізгі баптау — <b>от 5 000 ₸</b>\n"
        "• Полная + ПО / Толық + БЖ — <b>8–12 000 ₸</b>\n"
        "• ПК + камеры / камералар — <b>10–15 000 ₸</b>\n"
        "• Сборка / Жинау — <b>8–15 000 ₸</b>\n"
        "• Выезд / Шығу — по согласованию\n\n"
        "Точная смета после короткой диагностики.",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "🛠 <b>Услуги / Қызметтер</b>\n"
        "1) Настройка ПК / ПК баптау\n"
        "2) Сборка / апгрейд / Жинау\n"
        "3) ПК + HiWatch/Hikvision (SADP, iVMS, Hik-Connect)\n"
        "4) Удалёнка / офис / выезд\n\n"
        "📍 Тауке Хана 143, Шымкент",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def office(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "📍 <b>Шымкент, пр. Тауке Хана, 143</b>\n"
        "Пн–Пт 10–19 · Сб 10–16 · Вс по записи\n"
        "Дс–Жм 10–19 · Сб 10–16 · Жк жазылу бойынша\n\n"
        "Карта: сайт HikMart → Настройка ПК",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "ℹ️ <b>Помощь / Көмек</b>\n\n"
        "Просто пиши текстом — AI «Пирс» ответит:\n"
        "• бюджет (например <code>8000</code> или <code>бюджет 10к</code>)\n"
        "• Windows, вирусы, тормоза\n"
        "• камеры HiWatch / Hikvision\n"
        "• сборка ПК, апгрейд, сроки\n\n"
        "«📝 Оставить заявку» — заказ уйдёт оператору в ЛС.\n"
        "/order · /cancel · /id",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def kazakh_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "🇰🇿 <b>Қазақша сөйлесеміз!</b>\n\n"
        "Сұрағыңды қазақша жаз — мен (Пирс) қазақша жауап беремін.\n"
        "Өтінім: «📝 Оставить заявку» немесе /order\n"
        "Баға: 5 000 — 15 000 ₸\n"
        "Кеңсе: Шымкент, Тауке хан 143",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def order_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    await react(update.message, "lead")
    context.user_data.clear()
    await update.message.reply_text(
        "Ок, заявка 🔧\nКак тебя зовут? / Атыңыз кім?",
        reply_markup=menu(),
    )
    return NAME


async def order_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return NAME
    name = (update.message.text or "").strip()
    if len(name) < 2:
        await update.message.reply_text("Имя коротковато / Атыңызды толығырақ жазыңыз.")
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text("Телефон? / Телефон?\n(+7 775 …)")
    return PHONE


async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return PHONE
    raw = (update.message.text or "").strip()
    if len(re.sub(r"\D", "", raw)) < 10:
        await update.message.reply_text("Не похоже на телефон / Телефон дұрыс емес.")
        return PHONE
    context.user_data["phone"] = raw
    await update.message.reply_text("Какая услуга? / Қандай қызмет?", reply_markup=svc_kb())
    return SERVICE


async def order_service_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    if not q:
        return SERVICE
    await q.answer()
    code = (q.data or "").split(":")[-1]
    if code == "cancel":
        if q.message:
            await q.message.reply_text("Отменил / Болдырмады.", reply_markup=menu())
        return ConversationHandler.END
    context.user_data["service"] = SERVICE_MAP.get(code, "Консультация")
    if q.message:
        await q.message.reply_text(
            f"Услуга: <b>{escape(context.user_data['service'])}</b>\n"
            "Опиши задачу / Тапсырманы сипатта:",
            parse_mode=ParseMode.HTML,
        )
    return COMMENT


async def order_service_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return COMMENT
    context.user_data["service"] = (update.message.text or "Консультация").strip()
    await update.message.reply_text("Опиши задачу / Тапсырманы сипатта.")
    return COMMENT


async def order_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return COMMENT
    comment = (update.message.text or "").strip()
    if len(comment) < 3:
        await update.message.reply_text("Чуть подробнее / Толығырақ жазыңыз.")
        return COMMENT

    data = context.user_data
    await react(update.message, "ok")
    u = update.effective_user
    name = str(data.get("name", "—"))
    phone = str(data.get("phone", "—"))
    service = str(data.get("service", "—"))

    delivered = await notify_lead(
        context,
        user_tag=user_tag(update),
        name=name,
        phone=phone,
        service=service,
        comment=comment,
        user_id=u.id if u else None,
        username=u.username if u else None,
    )
    # дубль: переслать исходное сообщение админу
    if delivered and resolve_admin_id():
        try:
            await update.message.forward(resolve_admin_id())
        except Exception:
            pass

    if delivered:
        await update.message.reply_text(
            "✅ <b>Заявка принята / Өтінім қабылданды!</b>\n"
            f"Имя: <b>{escape(name)}</b>\n"
            f"Услуга: <b>{escape(service)}</b>\n\n"
            f"Оператор @{settings.admin_username} уже получил заявку в ЛС.\n"
            "Ответ обычно 15–30 мин.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu(),
        )
    else:
        await update.message.reply_text(
            "✅ Заявку сохранили, но оператор ещё не привязан.\n"
            f"@{settings.admin_username} должен написать боту /setadmin",
            reply_markup=menu(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("Ок, отменил / Болдырмады.", reply_markup=menu())
    return ConversationHandler.END


async def ask_pierce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await react(update.message, "think")
    await update.message.reply_text(
        "Я на линии ⚡ Задай <b>любой</b> вопрос.\n\n"
        "Примеры:\n"
        "• «бюджет 8000» / «10к на настройку»\n"
        "• «тормозит Windows»\n"
        "• «нужны камеры HiWatch»\n"
        "• «собрать ПК на 250 тысяч»\n\n"
        "Пиши просто текстом — отвечу, что можно сделать и по цене.\n"
        "Кез келген сұрақты жаз — жауап беремін.",
        parse_mode=ParseMode.HTML,
        reply_markup=menu(),
    )


async def free_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Любой текст → AI-консультант (бюджет, услуги, вопросы)."""
    if not update.message or not update.effective_user:
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    u = update.effective_user
    if ensure_admin_from_user(u):
        set_admin_id(update.effective_chat.id)

    uid = u.id
    is_admin = (u.username or "").lower().lstrip("@") == settings.admin_username.lower()

    # админские команды-подсказки
    if is_admin and text.lower() in {"/status", "status", "статус"}:
        from bot.services.notify import resolve_admin_id

        await update.message.reply_text(
            f"Admin chat_id={resolve_admin_id()}\nAI={'on' if settings.xai_api_key else 'off'}",
            reply_markup=menu(),
        )
        return

    if not is_admin:
        await notify_user_message(
            context,
            user_tag=user_tag(update),
            text=text,
            user_id=uid,
            username=u.username,
        )

    hist = push_history(uid, "user", text, limit=12)
    history = [{"role": h["role"], "content": h["content"]} for h in hist[:-1]]
    try:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    except Exception:
        pass

    reply = await grok_reply(text, history=history)
    push_history(uid, "assistant", reply, limit=12)

    # Telegram HTML: AI может прислать markdown — шлём plain, безопаснее
    try:
        await update.message.reply_text(reply, reply_markup=menu())
    except Exception as e:
        log.exception("reply fail: %s", e)
        try:
            await update.message.reply_text(
                reply[:3500],
                reply_markup=menu(),
                disable_web_page_preview=True,
            )
        except Exception:
            await update.message.reply_text(
                "Сбой отправки. Повтори вопрос или жми «Оставить заявку».",
                reply_markup=menu(),
            )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Conflict):
        log.error(
            "Conflict: другой экземпляр бота уже polling. "
            "Закрой второе окно python -m bot.main"
        )
        return
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning("Network: %s", err)
        return
    log.exception("Update error: %s", err)


def _print_token_help() -> None:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    print(
        "\n"
        "══════════════════════════════════════════════════\n"
        "  ОШИБКА: нет BOT_TOKEN\n"
        "══════════════════════════════════════════════════\n"
        f"  Папка бота: {root}\n"
        f"  Нужен файл: {env_path}\n\n"
        "  1) Скопируй .env.example → .env\n"
        "  2) Открой .env в Блокноте\n"
        "  3) Вставь:\n"
        "       BOT_TOKEN=токен_от_BotFather\n"
        "       XAI_API_KEY=ключ_xAI\n"
        "       ADMIN_USERNAME=STPierce\n"
        "  4) Сохрани UTF-8 и снова: python -m bot.main\n"
        "  Или запусти START.bat\n"
        "══════════════════════════════════════════════════\n"
    )


def main() -> None:
    if not settings.bot_token:
        log.error("Set BOT_TOKEN in .env (@BotFather) — file next to bot folder")
        _print_token_help()
        sys.exit(1)

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = (
        Application.builder()
        .token(settings.bot_token)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("order", order_entry),
            MessageHandler(filters.Regex(r"^📝 Оставить заявку$"), order_entry),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone)],
            SERVICE: [
                CallbackQueryHandler(order_service_cb, pattern=r"^svc:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_service_text),
            ],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_comment)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex(r"^❌"), cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("setadmin", cmd_setadmin))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.Regex(r"^ℹ️ Помощь$"), help_cmd))
    app.add_handler(MessageHandler(filters.Regex(r"^💰 Цены$"), prices))
    app.add_handler(MessageHandler(filters.Regex(r"^🛠 Услуги$"), services))
    app.add_handler(MessageHandler(filters.Regex(r"^📍 Офис$"), office))
    app.add_handler(MessageHandler(filters.Regex(r"^💬 Спросить Пирса$"), ask_pierce))
    app.add_handler(MessageHandler(filters.Regex(r"^🇰🇿 Қазақша$"), kazakh_hint))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_chat))
    app.add_error_handler(on_error)

    admin = resolve_admin_id()
    log.info(
        "Pierce bot starting… admin=@%s chat_id=%s",
        settings.admin_username,
        admin or "NOT_SET → /setadmin",
    )
    print(f"Bot OK — admin=@{settings.admin_username} id={admin or 'need /setadmin'}")
    print("Stop: Ctrl+C")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

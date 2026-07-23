"""
HiWatch Settings Bot — чистый Python, без внешних библиотек.
Минималистичная версия: без ИИ, без цветных кнопок.
Использует только requests для Telegram API.
"""
import os
import json
import time
import logging
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
ADMIN_USERNAMES = [
    u.strip().lstrip("@").lower()
    for u in (os.getenv("ADMIN_USERNAMES") or "STPierce,Who_Knyaz").replace(";", ",").split(",")
    if u.strip()
]
ADMIN_CHAT_IDS = []
_DEFAULT_IDS = "1930108146,1418146556"
_raw = os.getenv("ADMIN_CHAT_IDS") or os.getenv("ADMIN_CHAT_ID") or _DEFAULT_IDS
for _id in _raw.replace(";", ",").split(","):
    _id = _id.strip()
    if _id.lstrip("-").isdigit():
        cid = int(_id)
        if cid not in ADMIN_CHAT_IDS:
            ADMIN_CHAT_IDS.append(cid)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

USER_STATE: dict[int, dict] = {}

MENU = {
    "keyboard": [
        [{"text": "📝 Оставить заявку"}, {"text": "💰 Цены"}],
        [{"text": "🛠 Услуги"}, {"text": "📍 Офис"}],
        [{"text": "❓ Помощь"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

SVC_KB = {
    "inline_keyboard": [
        [{"text": "💻 Настройка ПК · от 8 000 ₸", "callback_data": "svc:setup"}],
        [{"text": "🔧 Сборка / апгрейд · от 12 000 ₸", "callback_data": "svc:build"}],
        [{"text": "📹 Видеонаблюдение · от 15 000 ₸", "callback_data": "svc:surv"}],
        [{"text": "💬 Консультация / другое", "callback_data": "svc:other"}],
        [{"text": "✕ Отмена", "callback_data": "svc:cancel"}],
    ]
}

SERVICE_MAP = {
    "setup": "Настройка ПК",
    "build": "Сборка / апгрейд",
    "surv": "ПК + видеонаблюдение",
    "other": "Консультация / другое",
}

WELCOME = (
    "Здравствуйте!\n"
    "Я бот HiWatch Settings — настройка ПК, сборка и видеонаблюдение в Шымкенте.\n\n"
    "Что я умею:\n"
    "📝 — оставить заявку (менеджер свяжется с вами)\n"
    "💰 — цены и услуги\n"
    "🛠 — список услуг\n"
    "📍 — офис и контакты\n\n"
    "Нажмите кнопку ниже 👇"
)

PRICES = (
    "💰 Цены и услуги\n\n"
    "Настройка ПК — от 8 000 до 20 000 ₸\n"
    "Установка Windows 10/11, драйверов, программ, оптимизация\n\n"
    "Сборка / апгрейд ПК — от 12 000 до 30 000 ₸\n"
    "Подбор комплектующих, сборка с MX-6, стресс-тест\n\n"
    "ПК + видеонаблюдение — от 15 000 до 35 000 ₸\n"
    "Hikvision, HiWatch: SADP, iVMS-4200, Hik-Connect, архив\n\n"
    "Консультация — бесплатно\n\n"
    "Выезд по Шымкенту бесплатно. Гарантия 30 дней."
)

SERVICES = (
    "🛠 Услуги\n\n"
    "✓ Настройка ПК (Windows, Linux)\n"
    "✓ Установка драйверов и программ\n"
    "✓ Сборка ПК с нуля\n"
    "✓ Апгрейд существующего ПК\n"
    "✓ Настройка видеонаблюдения (Hikvision, HiWatch, Dahua)\n"
    "✓ Удалённая помощь\n"
    "✓ Диагностика и ремонт\n"
    "✓ Консультации по подбору техники\n\n"
    "Нажмите «📝 Оставить заявку» — менеджер свяжется!"
)

OFFICE = (
    "📍 Офис и контакты\n\n"
    "Шымкент, пр. Тауке Хана, 143\n"
    "📞 +7 (708) 001-12-12\n"
    "🌐 hikmart.kz\n"
    "📷 @hikmart.kz\n\n"
    "Режим: Пн–Сб, 10:00 – 20:00"
)

HELP_TXT = (
    "❓ Помощь\n\n"
    "📝 Оставить заявку — опишите проблему, менеджер свяжется\n"
    "💰 Цены и услуги — прайс-лист\n"
    "📍 Офис и контакты — адрес, телефон\n\n"
    "Команды: /start, /order, /help"
)


def set_state(cid, step, **extra):
    s = USER_STATE.get(cid, {})
    s["step"] = step
    s.update(extra)
    USER_STATE[cid] = s


def get_state(cid):
    return USER_STATE.get(cid, {})


def clear_state(cid):
    USER_STATE.pop(cid, None)


def tg(method, **params):
    try:
        r = requests.post(f"{BASE}/{method}", json=params, timeout=25)
        return r.json()
    except Exception as e:
        log.error(f"tg {method}: {e}")
        return {}


def send(chat_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "text": text[:4000]}
    if reply_markup is not None:
        p["reply_markup"] = reply_markup
    return tg("sendMessage", **p)


def notify_admins(text):
    for cid in ADMIN_CHAT_IDS:
        try:
            tg("sendMessage", chat_id=cid, text=text[:3900])
        except Exception as e:
            log.warning(f"notify {cid}: {e}")


def now_str():
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=6))
    return datetime.now(tz).strftime("%d.%m.%Y %H:%M")


def build_order(user, state):
    name = state.get("name", "—")
    phone = state.get("phone", "—")
    service = state.get("service", "—")
    problem = state.get("problem", "—")
    un = f"@{user['username']}" if user.get("username") else "нет"
    full = user.get("first_name", "") + " " + (user.get("last_name") or "")
    uid = user.get("id", "—")
    return (
        "📝 НОВАЯ ЗАЯВКА\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Услуга: {service}\n"
        f"Описание: {problem}\n\n"
        f"Telegram: {un}\n"
        f"Имя в TG: {full.strip()}\n"
        f"ID: {uid}\n\n"
        f"Время: {now_str()}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def handle_start(chat_id, user):
    uname = (user.get("username") or "").lower()
    if uname in ADMIN_USERNAMES:
        cid = user.get("id")
        if cid and cid not in ADMIN_CHAT_IDS:
            ADMIN_CHAT_IDS.append(cid)
            log.info(f"Admin bound: @{uname} → {cid}")
    clear_state(user.get("id", chat_id))
    send(chat_id, WELCOME, reply_markup=MENU)


def handle_callback(update):
    cbq = update.get("callback_query", {})
    data = cbq.get("data", "")
    msg = cbq.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user = cbq.get("from", {})
    if not chat_id:
        return
    tg("answerCallbackQuery", callback_query_id=cbq.get("id"))
    uid = user.get("id", chat_id)

    if data.startswith("svc:"):
        action = data.split(":", 1)[1]
        if action == "cancel":
            clear_state(uid)
            tg("editMessageText", chat_id=chat_id, message_id=msg.get("message_id"),
               text="✕ Заявка отменена.")
            send(chat_id, "Можно начать заново в любой момент.", MENU)
            return
        label = SERVICE_MAP.get(action, "Консультация / другое")
        set_state(uid, "name", service=label)
        tg("editMessageText", chat_id=chat_id, message_id=msg.get("message_id"),
           text=f"📝 Заявка — {label}\n\nВведите ваше имя:\n(например: Алексей)")


def handle_message(update):
    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return
    user = msg.get("from", {})
    text = (msg.get("text") or "").strip()
    uid = user.get("id", chat_id)

    if text.startswith("/start"):
        handle_start(chat_id, user)
        return
    if text.startswith("/order"):
        set_state(uid, "svc")
        send(chat_id, "📝 Заявка\n\nВыберите нужную услугу:", SVC_KB)
        return
    if text.startswith("/help"):
        send(chat_id, HELP_TXT, MENU)
        return
    if text.startswith("/id"):
        send(chat_id, f"Ваш chat_id: {uid}")
        return
    if text.startswith("/cancel"):
        clear_state(uid)
        send(chat_id, "✕ Заявка отменена.", MENU)
        return

    # Отмена
    if "Отмена" in text or text == "✕ Отмена":
        clear_state(uid)
        send(chat_id, "✕ Заявка отменена. Можно начать заново в любой момент.", MENU)
        return

    # Меню
    if "Оставить заявку" in text:
        set_state(uid, "svc")
        send(chat_id, "📝 Заявка\n\nВыберите нужную услугу:", SVC_KB)
        return
    if "Цены" in text or "цены" in text:
        send(chat_id, PRICES)
        return
    if "Услуги" in text or "услуги" in text:
        send(chat_id, SERVICES)
        return
    if "Офис" in text or "офис" in text or "контакт" in text:
        send(chat_id, OFFICE)
        return
    if "Помощь" in text or "помощь" in text:
        send(chat_id, HELP_TXT)
        return

    # FSM
    state = get_state(uid)
    step = state.get("step", "")

    if step == "name":
        if len(text) < 2:
            send(chat_id, "❌ Имя слишком короткое. Введите ещё раз:")
            return
        set_state(uid, "phone", name=text, service=state.get("service", "—"))
        send(chat_id, "📞 Введите ваш номер телефона:\n(например: +7 708 001 12 12)")
        return

    if step == "phone":
        digits = "".join(c for c in text if c.isdigit())
        if len(digits) < 7:
            send(chat_id, "❌ Неверный номер. Введите ещё раз:\n(например: +7 708 001 12 12)")
            return
        set_state(uid, "problem", name=state.get("name", ""), phone=text, service=state.get("service", "—"))
        send(chat_id, "Опишите проблему или что нужно сделать:\n(например: ПК тормозит, переустановить Windows)")
        return

    if step == "problem":
        if len(text) < 3:
            send(chat_id, "❌ Опишите подробнее (минимум 3 символа):")
            return
        state["problem"] = text
        order_msg = build_order(user, state)
        notify_admins(order_msg)
        send(chat_id, "✅ Заявка принята!\n\nМенеджер свяжется с вами в ближайшее время.\nСпасибо!", MENU)
        clear_state(uid)
        return

    # Неизвестный текст
    send(chat_id, "Используйте кнопки меню 👇", MENU)


def handle_update(update):
    if update.get("callback_query"):
        handle_callback(update)
    else:
        handle_message(update)


# ─── Flask webhook (for Render/Koyeb) ────────────────
try:
    from flask import Flask, request as flask_request
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "HiWatch Settings Bot — running"

    @app.route(f"/{BOT_TOKEN}", methods=["POST"])
    def webhook():
        update = flask_request.get_json(force=True)
        try:
            handle_update(update)
        except Exception as e:
            log.error(f"handle_update: {e}")
        return "ok"

    @app.route("/setwebhook")
    def set_webhook():
        url = flask_request.host_url
        r = tg("setWebhook", url=f"{url}{BOT_TOKEN}")
        return json.dumps(r)

except ImportError:
    app = None


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден!")
        exit(1)

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if webhook_url and app:
        port = int(os.getenv("PORT", "10000"))
        tg("setWebhook", url=f"{webhook_url}/{BOT_TOKEN}")
        log.info(f"Webhook set: {webhook_url}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=port)
    else:
        # Polling mode
        log.info("Bot started (polling)")
        offset = 0
        while True:
            try:
                r = requests.get(f"{BASE}/getUpdates",
                                 params={"offset": offset, "timeout": 30}, timeout=35)
                j = r.json()
                if not j.get("ok"):
                    log.error(f"getUpdates: {j}")
                    time.sleep(3)
                    continue
                for upd in j.get("result", []):
                    offset = upd.get("update_id", 0) + 1
                    try:
                        handle_update(upd)
                    except Exception as e:
                        log.error(f"handle: {e}")
            except Exception as e:
                log.error(f"poll: {e}")
                time.sleep(3)

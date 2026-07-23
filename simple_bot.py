# -*- coding: utf-8 -*-
"""
HiWatch Settings Bot — минималистичная синхронная версия.
Без ИИ, без цветных кнопок. Чистый, быстрый, надёжный.
Заказы → @STPierce, @Who_Knyaz.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from bot.config import settings
from bot.services.notify import (
    ensure_admin_from_user,
    is_manager_username,
    manager_usernames,
    resolve_admin_ids,
)
from bot.storage import add_admin_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("simple-bot")

BASE = f"https://api.telegram.org/bot{settings.bot_token}"

MENU = {
    "keyboard": [
        [{"text": "📝 Оставить заявку"}, {"text": "💰 Цены"}],
        [{"text": "🛠 Услуги"}, {"text": "📍 Офис"}],
        [{"text": "❓ Помощь"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "input_field_placeholder": "Нажмите кнопку меню",
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

ORDERS: dict[int, dict] = {}
SERVICE_MAP = {
    "setup": "Настройка ПК",
    "build": "Сборка / апгрейд",
    "surv": "ПК + видеонаблюдение",
    "other": "Консультация / другое",
}

_POOL = ThreadPoolExecutor(max_workers=12, thread_name_prefix="hikwatch")
_HTTP: httpx.Client | None = None
_HTTP_LOCK = threading.Lock()


def http() -> httpx.Client:
    global _HTTP
    with _HTTP_LOCK:
        if _HTTP is None or _HTTP.is_closed:
            _HTTP = httpx.Client(
                timeout=httpx.Timeout(25.0, connect=6.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
            )
        return _HTTP


def api(method: str, **params) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, (dict, list)):
            data[k] = json.dumps(v, ensure_ascii=False)
        elif v is not None:
            data[k] = v
    try:
        r = http().post(f"{BASE}/{method}", data=data)
        j = r.json()
        if not j.get("ok"):
            log.warning("%s: %s", method, j.get("description", j))
        return j
    except Exception as e:
        log.error("api %s: %s", method, e)
        return {}


def send(chat_id: int, text: str, reply_markup=None) -> bool:
    p: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000]}
    if reply_markup is not None:
        p["reply_markup"] = reply_markup
    return bool(api("sendMessage", **p).get("ok"))


def notify_managers(text: str, *, critical: bool = True) -> int:
    """Отправить менеджерам в ЛС."""
    ids = resolve_admin_ids()
    if not ids:
        log.warning("No manager chat_ids — lead not delivered")
        return 0

    ok_n = 0

    def _one(cid: int) -> None:
        nonlocal ok_n
        try:
            if api("sendMessage", chat_id=cid, text=text[:3900]).get("ok"):
                ok_n += 1
        except Exception as e:
            log.error("notify %s: %s", cid, e)

    if critical:
        for cid in ids:
            _one(cid)
    else:
        for cid in ids:
            threading.Thread(target=_one, args=(cid,), daemon=True).start()
    return ok_n


def user_label(msg: dict) -> str:
    u = msg.get("from") or {}
    name = u.get("first_name") or "?"
    un = u.get("username")
    uid = u.get("id")
    return f"{name} (@{un}, id={uid})" if un else f"{name} (id={uid})"


def handle_start(chat_id: int, msg: dict) -> None:
    u = msg.get("from") or {}
    uname = u.get("username")

    class U:
        pass

    uu = U()
    uu.username = uname
    uu.id = u.get("id")

    if ensure_admin_from_user(uu) or is_manager_username(uname):
        if u.get("id"):
            add_admin_id(int(u["id"]))
        send(
            chat_id,
            f"✅ Вы подключены как менеджер.\n"
            f"Заявки клиентов будут приходить вам в ЛС.\n"
            f"Менеджеры: {', '.join('@' + m for m in manager_usernames())}",
            MENU,
        )
        return

    name = u.get("first_name") or "друг"
    send(
        chat_id,
        f"Здравствуйте, {name}!\n"
        "Я бот HiWatch Settings — настройка ПК, сборка и видеонаблюдение в Шымкенте.\n\n"
        "Нажмите «📝 Оставить заявку» — менеджеры свяжутся с вами.",
        MENU,
    )


def deliver_order(chat_id: int, msg: dict, st: dict) -> None:
    """Заявка → менеджеры; клиенту — подтверждение."""
    lead = (
        "📝 НОВАЯ ЗАЯВКА\n"
        "────────────────\n"
        f"Клиент: {user_label(msg)}\n"
        f"Имя: {st.get('name')}\n"
        f"Тел: {st.get('phone')}\n"
        f"Услуга: {st.get('service')}\n"
        f"Описание: {st.get('comment')}\n"
        "────────────────\n"
        "Ответьте клиенту (звонок / WhatsApp / TG)."
    )
    delivered = notify_managers(lead, critical=True)
    log.info("order delivered to %s managers", delivered)

    send(
        chat_id,
        "✅ Заявка принята!\n\n"
        f"Имя: {st.get('name')}\n"
        f"Услуга: {st.get('service')}\n\n"
        "Менеджеры уже получили вашу заявку и свяжутся с вами "
        "в ближайшее время (обычно 15–30 минут в рабочее время).\n\n"
        "Спасибо, что выбрали нас!",
        MENU,
    )
    if delivered == 0:
        log.error("ORDER NOT DELIVERED — managers must /start bot once")


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


def handle_text(chat_id: int, msg: dict, text: str) -> None:
    u = msg.get("from") or {}
    uid = int(u.get("id") or chat_id)

    # Заявка в процессе
    st = ORDERS.get(chat_id)
    if st:
        step = st.get("step")
        if step == "name":
            if len(text.strip()) < 2:
                send(chat_id, "Укажите имя (минимум 2 символа):")
                return
            st["name"] = text.strip()
            st["step"] = "phone"
            send(chat_id, "📞 Введите ваш номер телефона:\n<i>(например: +7 708 001 12 12)</i>")
            return
        if step == "phone":
            digits = "".join(c for c in text if c.isdigit())
            if len(digits) < 7:
                send(chat_id, "❌ Неверный номер. Введите ещё раз:\n<i>(например: +7 708 001 12 12)</i>")
                return
            st["phone"] = text.strip()
            st["step"] = "comment"
            send(chat_id, "Опишите проблему или что нужно сделать:\n<i>(например: ПК тормозит, переустановить Windows)</i>")
            return
        if step == "comment":
            if len(text.strip()) < 3:
                send(chat_id, "Опишите подробнее (минимум 3 символа):")
                return
            st["comment"] = text.strip()
            deliver_order(chat_id, msg, st)
            ORDERS.pop(chat_id, None)
            return

    # Отмена
    if "Отмена" in text or text == "✕ Отмена":
        ORDERS.pop(chat_id, None)
        send(chat_id, "✕ Заявка отменена. Можно начать заново в любой момент.", MENU)
        return

    # Меню
    if "Оставить заявку" in text:
        ORDERS[chat_id] = {"step": "name", "service": "—"}
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

    # Неизвестный текст
    send(chat_id, "Используйте кнопки меню 👇", MENU)


def handle_callback(chat_id: int, msg: dict, data: str) -> None:
    u = msg.get("from") or {}
    uid = int(u.get("id") or chat_id)

    if data.startswith("svc:"):
        action = data.split(":", 1)[1]
        if action == "cancel":
            ORDERS.pop(chat_id, None)
            api("editMessageText", chat_id=chat_id, message_id=msg.get("message_id"),
                text="✕ Заявка отменена.")
            send(chat_id, "Можно начать заново в любой момент.", MENU)
            return
        label = SERVICE_MAP.get(action, "Консультация / другое")
        ORDERS[chat_id] = {"step": "name", "service": label}
        api("editMessageText", chat_id=chat_id, message_id=msg.get("message_id"),
            text=f"📝 Заявка — {label}\n\nВведите ваше имя:\n<i>(например: Алексей)</i>")
        return


def handle_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message") or {}
    cbq = update.get("callback_query")

    if cbq:
        chat_id = cbq.get("message", {}).get("chat", {}).get("id")
        data = cbq.get("data", "")
        if chat_id:
            api("answerCallbackQuery", callback_query_id=cbq.get("id"))
            handle_callback(int(chat_id), cbq.get("message", {}), data)
        return

    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return

    text = msg.get("text", "").strip()
    if text.startswith("/start"):
        handle_start(int(chat_id), msg)
        return
    if text.startswith("/order"):
        ORDERS[chat_id] = {"step": "name", "service": "—"}
        send(int(chat_id), "📝 Заявка\n\nВыберите нужную услугу:", SVC_KB)
        return
    if text.startswith("/help"):
        send(int(chat_id), HELP_TXT, MENU)
        return
    if text.startswith("/id"):
        uid = msg.get("from", {}).get("id", chat_id)
        send(int(chat_id), f"Ваш chat_id: {uid}")
        return
    if text.startswith("/cancel"):
        ORDERS.pop(chat_id, None)
        send(int(chat_id), "✕ Заявка отменена.", MENU)
        return

    if text:
        handle_text(int(chat_id), msg, text)


def poll() -> None:
    offset = 0
    log.info("Bot started (polling)")
    while True:
        try:
            r = http().get(f"{BASE}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            j = r.json()
            if not j.get("ok"):
                log.error("getUpdates: %s", j)
                time.sleep(3)
                continue
            for upd in j.get("result", []):
                offset = upd.get("update_id", 0) + 1
                _POOL.submit(handle_update, upd)
        except Exception as e:
            log.error("poll: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    if not settings.bot_token:
        print("❌ BOT_TOKEN не найден в .env!")
        exit(1)
    poll()

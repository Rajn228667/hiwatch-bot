"""xAI Grok + мгновенные локальные ответы (бюджет / FAQ)."""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from bot.config import settings
from bot.knowledge import BUDGET_FALLBACK_RU, SYSTEM_PROMPT

log = logging.getLogger(__name__)

# Жёсткий лимит — клиент не ждёт вечность
_TIMEOUT = httpx.Timeout(12.0, connect=6.0)
_CLIENT: httpx.Client | None = None


def _client() -> httpx.Client:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.Client(timeout=_TIMEOUT, http2=False)
    return _CLIENT


_RE_BUDGET_WORD = re.compile(
    r"бюджет|баға|бага|money|budget|есть\s+\d|бар\s+\d|могу\s+на|төлеу|теңге|тенге|тенге|₸",
    re.IGNORECASE,
)


def extract_budget_tenge(text: str) -> int | None:
    t = (text or "").strip().lower().replace("ё", "е")
    if not t:
        return None

    m = re.search(r"(\d+[.,]?\d*)\s*(к|k|тыс)", t, re.I)
    if m:
        n = float(m.group(1).replace(",", "."))
        return int(n * 1000)

    amounts: list[int] = []
    for m in re.finditer(r"(?<!\d)(\d{4,7})(?!\d)", t):
        amounts.append(int(m.group(1)))
    for m in re.finditer(r"(?<!\d)(\d{1,3}(?:[ \u00a0]\d{3})+)(?!\d)", t):
        amounts.append(int(re.sub(r"\s", "", m.group(1))))

    if not amounts:
        return None

    is_budgetish = bool(_RE_BUDGET_WORD.search(t)) or len(t) <= 28
    if not is_budgetish and len(t) > 28:
        return None

    candidates = [a for a in amounts if 1000 <= a <= 5_000_000]
    return max(candidates) if candidates else None


def is_hardware_budget(amount: int, text: str) -> bool:
    t = (text or "").lower()
    if any(
        w in t
        for w in (
            "желез",
            "сборк",
            "комплект",
            "видеокарт",
            "gpu",
            "процессор",
            "пк купить",
            "купить пк",
            "жинау",
        )
    ):
        return True
    return amount >= 50_000


def offline_budget_reply(amount: int, text: str) -> str:
    if is_hardware_budget(amount, text):
        return (
            f"Ок, ~{amount:,} ₸ на железо/ПК.\n".replace(",", " ")
            + BUDGET_FALLBACK_RU["iron"]
            + "\n\n→ «📝 Оставить заявку» — зафиксируем."
        )

    if amount < 5000:
        body = BUDGET_FALLBACK_RU["low"]
    elif amount < 8000:
        body = BUDGET_FALLBACK_RU["5"]
    elif amount < 10000:
        body = BUDGET_FALLBACK_RU["8"]
    elif amount < 13000:
        body = BUDGET_FALLBACK_RU["10"]
    else:
        body = BUDGET_FALLBACK_RU["15"]

    return (
        f"Ок, бюджет ~{amount:,} ₸ на работу мастера.\n".replace(",", " ")
        + body
        + "\n\nНапиши задачу (Windows / камеры / сборка) или «📝 Оставить заявку»."
    )


# Мгновенные ответы без AI (часто задаваемые)
_FAST_FAQ: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"цена|стоимость|сколько\s*стоит|прайс|баға|қанша", re.I),
        "💰 Прайс (работа):\n"
        "• от 5 000 ₸ — базовая настройка\n"
        "• 8–12 000 ₸ — полная настройка + ПО\n"
        "• 10–15 000 ₸ — ПК + камеры (iVMS/SADP)\n"
        "• 8–15 000 ₸ — сборка/апгрейд\n"
        "Напиши свой бюджет числом — скажу, что реально сделать.",
    ),
    (
        re.compile(r"адрес|где\s*офис|как\s*добраться|локац|мекенжай|қайда", re.I),
        "📍 Офис: Шымкент, пр. Тауке Хана, 143\n"
        "Пн–Пт 10:00–19:00 · Сб 10:00–16:00\n"
        "Можно удалённо (AnyDesk) или выезд — по заявке.",
    ),
    (
        re.compile(r"удал[её]н|anydesk|дистанц|қашық", re.I),
        "Да, работаем удалённо: AnyDesk / Telegram.\n"
        "Настройка ПО, драйверы, iVMS — без визита.\n"
        "Сборка железа — офис или выезд. Жми «📝 Оставить заявку».",
    ),
    (
        re.compile(r"камер|ivms|sadp|hik-?connect|hiwatch|hikvision|видеонаблюд|бейне", re.I),
        "Камеры HiWatch/Hikvision — наш профиль 🔧\n"
        "SADP + iVMS-4200 + Hik-Connect, сеть, права, инструкция.\n"
        "Ориентир 10 000–15 000 ₸. Опиши сколько камер / NVR — уточним.",
    ),
    (
        re.compile(r"тормоз|вирус|синий\s*экран|висит|медленно|windows|винда|ож\b", re.I),
        "Похоже на софт-проблему.\n"
        "• от 5 000 ₸ — диагностика, драйверы, оптимизация\n"
        "• 8–12 000 ₸ — полная настройка / восстановление Windows\n"
        "Напиши, что именно происходит, или оставь заявку.",
    ),
    (
        re.compile(r"выезд|приехать|на\s*дом|шығу", re.I),
        "Выезд по Шымкенту — да, по согласованию (обычно + к базовой).\n"
        "Оставь заявку с адресом/районом — оператор подтвердит.",
    ),
    (
        re.compile(r"срок|как\s*быстро|сегодня|срочно|мерзім|шұғыл", re.I),
        "Обычно 1–2 дня. Срочно — в приоритете в рабочее время.\n"
        "Заявка 24/7, ответ ~15–30 мин. Жми «📝 Оставить заявку».",
    ),
    (
        re.compile(r"привет|здравств|салам|сәлем|hello|hi\b|қош", re.I),
        "Привет! Я Пирс ⚡\n"
        "Настройка/сборка ПК, камеры, Windows — Шымкент.\n"
        "Напиши бюджет или задачу — сразу скажу, что можно сделать.",
    ),
]


def fast_local_reply(text: str) -> Optional[str]:
    """Мгновенный ответ без сети (бюджет / FAQ). None = нужен AI."""
    t = (text or "").strip()
    if not t:
        return "Напиши вопрос: бюджет, Windows, камеры, сборка."

    amount = extract_budget_tenge(t)
    # Чистый бюджет или «бюджет 8к» — отвечаем сразу, без Grok
    if amount and (
        bool(_RE_BUDGET_WORD.search(t))
        or len(t) <= 32
        or re.fullmatch(r"[\d\sкkтыс.\-₸тгтенгебағбюджет]+", t.lower().replace("ё", "е"))
    ):
        return offline_budget_reply(amount, t).replace("<b>", "").replace("</b>", "")

    for pat, ans in _FAST_FAQ:
        if pat.search(t):
            # если ещё и бюджет в длинном тексте — добавим хвост
            if amount:
                return ans + "\n\n" + offline_budget_reply(amount, t).replace("<b>", "").replace(
                    "</b>", ""
                )
            return ans
    return None


def enrich_user_message(user_text: str) -> str:
    amount = extract_budget_tenge(user_text)
    if not amount:
        return user_text
    kind = (
        "железо/сборка ПК"
        if is_hardware_budget(amount, user_text)
        else "работа мастера"
    )
    return (
        f"{user_text}\n\n"
        f"[Сумма ≈ {amount} ₸, тип: {kind}. "
        f"2–3 варианта из базы, затем заявка.]"
    )


def grok_reply_sync(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Синхронный быстрый ответ (для simple_bot)."""
    text = (user_text or "").strip()
    if not text:
        return "Напиши вопрос: бюджет, Windows, камеры, сборка."

    # 1) мгновенный локальный
    local = fast_local_reply(text)
    if local:
        return local

    # 2) без ключа — короткий FAQ
    if not settings.xai_api_key:
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return (
            "• от 5 000 ₸ — базовая настройка\n"
            "• 8–12 000 ₸ — полная\n"
            "• 10–15 000 ₸ — ПК + камеры\n"
            "• 8–15 000 ₸ — сборка (работа)\n\n"
            "Напиши бюджет числом или «📝 Оставить заявку»."
        )

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-4:])  # меньше = быстрее
    messages.append({"role": "user", "content": enrich_user_message(text)})

    url = f"{settings.xai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.xai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.xai_model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 280,  # короче = быстрее
    }

    try:
        r = _client().post(url, json=payload, headers=headers)
        data = r.json()
        if r.status_code >= 400:
            log.error("Grok %s: %s", r.status_code, data)
            amount = extract_budget_tenge(text)
            if amount:
                return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
            return "Сеть AI моргнула. Повтори коротко или «Оставить заявку»."
        content = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        ).strip()
        if content:
            return content
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return "Не расслышал — ещё раз коротко или бюджет числом."
    except httpx.TimeoutException:
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return (
            "AI долго отвечает. Напиши бюджет (8000) или задачу одним предложением.\n"
            "Либо сразу «📝 Оставить заявку»."
        )
    except Exception as e:
        log.exception("Grok fail: %s", e)
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return "Связь с AI упала. Жми «Оставить заявку» — оператор ответит."


async def grok_reply(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Async-обёртка (совместимость с PTB main)."""
    return grok_reply_sync(user_text, history)

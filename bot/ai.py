"""xAI Grok + локальные подсказки по бюджету/вопросам."""

from __future__ import annotations

import logging
import re

import httpx

from bot.config import settings
from bot.knowledge import BUDGET_FALLBACK_RU, SYSTEM_PROMPT

log = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(28.0, connect=12.0)

# числа вроде 8000, 10к, 10 000, 15тыс, 100000
_RE_MONEY = re.compile(
    r"(?P<n>\d[\d\s]{0,8})\s*(?P<u>тыс\.?|тысяч[аи]?|к|k|тг|₸|тенге)?",
    re.IGNORECASE,
)
_RE_BUDGET_WORD = re.compile(
    r"бюджет|баға|бага|money|budget|есть\s+\d|бар\s+\d|могу\s+на|төлеу|теңге|тенге",
    re.IGNORECASE,
)


def extract_budget_tenge(text: str) -> int | None:
    """Достать сумму в тенге из фразы клиента (если похоже на бюджет)."""
    t = (text or "").strip().lower().replace("ё", "е")
    if not t:
        return None

    # «10к», «10 k», «15тыс»
    m = re.search(r"(\d+[.,]?\d*)\s*(к|k|тыс)", t, re.I)
    if m:
        n = float(m.group(1).replace(",", "."))
        return int(n * 1000)

    # голые суммы 5000–999999 если есть слово бюджет или короткое «8000»
    amounts: list[int] = []
    for m in re.finditer(r"\b(\d{4,7})\b", t.replace(" ", "")):
        amounts.append(int(m.group(1)))
    for m in re.finditer(r"\b(\d{1,3}(?:\s\d{3})+)\b", t):
        amounts.append(int(re.sub(r"\s", "", m.group(1))))

    if not amounts:
        return None

    # если явно про бюджет или одно короткое сообщение с числом
    is_budgetish = bool(_RE_BUDGET_WORD.search(t)) or (
        len(t) <= 24 and any(a >= 3000 for a in amounts)
    )
    if not is_budgetish and not re.search(r"\d", t):
        return None
    if not is_budgetish and len(t) > 40:
        # длинный текст без слова бюджет — не навязываем
        return None

    # берём наиболее правдоподобную сумму
    candidates = [a for a in amounts if 1000 <= a <= 5_000_000]
    if not candidates:
        return None
    return max(candidates)


def is_hardware_budget(amount: int, text: str) -> bool:
    t = (text or "").lower()
    if any(w in t for w in ("желез", "сборк", "комплект", "видеокарт", "gpu", "процессор", "пк купить")):
        return True
    # большие суммы почти всегда железо
    return amount >= 50_000


def offline_budget_reply(amount: int, text: str) -> str:
    if is_hardware_budget(amount, text):
        return (
            f"Понял, ориентир ~{amount:,} ₸ ".replace(",", " ")
            + BUDGET_FALLBACK_RU["iron"]
            + "\n\nЖми «📝 Оставить заявку» — зафиксируем задачу."
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
        f"Ок, бюджет около <b>{amount:,} ₸</b> на работу.\n".replace(",", " ")
        + body
        + "\n\nНапиши задачу (Windows / камеры / сборка) или «📝 Оставить заявку»."
    )


def enrich_user_message(user_text: str) -> str:
    """Добавить скрытый контекст для модели, если виден бюджет."""
    amount = extract_budget_tenge(user_text)
    if not amount:
        return user_text
    kind = "железо/сборка ПК" if is_hardware_budget(amount, user_text) else "работа мастера (настройка/сборка-услуга)"
    return (
        f"{user_text}\n\n"
        f"[Системная подсказка: клиент указал сумму ≈ {amount} ₸, "
        f"скорее всего бюджет на {kind}. "
        f"Дай 2–3 конкретных варианта что можно сделать, цены из базы, "
        f"затем предложи заявку.]"
    )


async def grok_reply(
    user_text: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    text = (user_text or "").strip()
    if not text:
        return "Напиши вопрос: бюджет, Windows, камеры, сборка — отвечу по делу."

    # быстрый офлайн-ответ если нет ключа
    if not settings.xai_api_key:
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return (
            "Могу сориентировать по услугам:\n"
            "• 5 000+ ₸ — базовая настройка\n"
            "• 8–12 000 ₸ — полная настройка\n"
            "• 10–15 000 ₸ — ПК + камеры / сложные задачи\n"
            "• 8–15 000 ₸ — сборка/апгрейд (работа)\n\n"
            "Напиши бюджет числом (например 10000) или жми «📝 Оставить заявку»."
        )

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-8:])
    messages.append({"role": "user", "content": enrich_user_message(text)})

    url = f"{settings.xai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.xai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.xai_model,
        "messages": messages,
        "temperature": 0.55,
        "max_tokens": 520,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(url, json=payload, headers=headers)
            data = r.json()
            if r.status_code >= 400:
                log.error("Grok %s: %s", r.status_code, data)
                amount = extract_budget_tenge(text)
                if amount:
                    return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
                return (
                    "AI канал моргнул 😅 Повтори вопрос или напиши бюджет числом "
                    "(например 8000). Либо «Оставить заявку»."
                )
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content:
                return content
            amount = extract_budget_tenge(text)
            if amount:
                return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
            return "Не расслышал — напиши ещё раз: бюджет, задача или «Оставить заявку»."
    except httpx.TimeoutException:
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return "AI долго думает. Напиши бюджет числом или оставь заявку кнопкой."
    except Exception as e:
        log.exception("Grok fail: %s", e)
        amount = extract_budget_tenge(text)
        if amount:
            return offline_budget_reply(amount, text).replace("<b>", "").replace("</b>", "")
        return "Связь с AI упала. Напиши бюджет/задачу коротко или кнопку заявки."

# HiWatch Settings Bot

Telegram бот для приёма заявок на настройку ПК, сборку, видеонаблюдение.

## Возможности

- **Быстрый flow заявки**: имя → номер → описание проблемы ПК → менеджер связывается
- **Заказы в ЛС админам**: @STPierce и @who_knyaz получают все заявки
- **Цветные кнопки**: визуальное разделение (🟢🔵🟡🟣⚪)
- **ИИ-ассистент Пирс**: ответы на вопросы про ПК (Grok API + локальные ответы)
- **Асинхронный**: python-telegram-bot 21+, быстро и надёжно

## Установка (локально)

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполнить BOT_TOKEN в .env
python bot.py
```

## Деплой на Render (бесплатно, 24/7)

1. Залить код на GitHub
2. Зайти на https://render.com → New → Web Service
3. Выбрать репозиторий
4. Render автоматически определит `render.yaml`
5. Добавить env vars:
   - `BOT_TOKEN` — токен бота
   - `ADMIN_USERNAMES` — `STPierce,who_knyaz`
   - `XAI_API_KEY` — ключ Grok (опционально)
   - `WEBHOOK_URL` — `https://your-app.onrender.com`
6. Deploy → бот работает 24/7

## Деплой на Koyeb (бесплатно, всегда включён)

1. Залить код на GitHub
2. Зайти на https://app.koyeb.com → Create Service → GitHub
3. Выбрать репозиторий
4. Build command: `pip install -r requirements.txt`
5. Run command: `python bot.py`
6. Port: 10000
7. Добавить env vars (BOT_TOKEN, ADMIN_USERNAMES, XAI_API_KEY, WEBHOOK_URL)
8. Deploy

## Команды

- `/start` — приветствие + главное меню
- `/order` — оставить заявку
- `/setadmin` — привязать менеджера (только для @STPierce, @who_knyaz)
- `/id` — показать chat_id
- `/help` — помощь

## Flow заявки

1. Пользователь нажимает 🟢 «Оставить заявку»
2. Вводит имя
3. Вводит номер телефона
4. Описывает проблему с ПК
5. Заявка отправляется в ЛС @STPierce и @who_knyaz
6. Менеджер связывается с клиентом, обсуждает цену/адрес/время

# HiWatch Settings Bot

Telegram бот для приёма заявок на настройку ПК, сборку, видеонаблюдение.
Минималистичный, профессиональный, без лишнего.

## Возможности

- **Простой flow заявки**: выбор услуги → имя → номер → описание → менеджер связывается
- **Заказы в ЛС админам**: @STPierce и @Who_Knyaz получают все заявки
- **Минималистичный дизайн**: чистые кнопки, без цветных квадратов, Telegram Premium эмодзи
- **Без ИИ**: только заявки, цены, услуги, контакты — быстро и надёжно
- **Асинхронный**: python-telegram-bot 21+

## Установка (локально)

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполнить BOT_TOKEN в .env
python bot.py
```

## Бесплатный хостинг (24/7)

### Вариант 1: Render (рекомендуется)

1. Залить код на GitHub
2. Зайти на https://render.com → New → Web Service
3. Выбрать репозиторий
4. Render автоматически определит `render.yaml`
5. Добавить env vars:
   - `BOT_TOKEN` — токен бота от @BotFather
   - `ADMIN_USERNAMES` — `STPierce,Who_Knyaz`
   - `ADMIN_CHAT_IDS` — ваши chat_id (узнать через /id в боте)
6. Deploy → бот работает 24/7

### Вариант 2: Koyeb

1. Залить код на GitHub
2. Зайти на https://koyeb.com → Create Service
3. Выбрать GitHub репозиторий
4. Koyeb определит `koyeb.yaml`
5. Добавить env vars (BOT_TOKEN, ADMIN_USERNAMES, ADMIN_CHAT_IDS)
6. Deploy

### Вариант 3: Railway

1. Залить код на GitHub
2. Зайти на https://railway.app → New Project → Deploy from GitHub
3. Добавить env vars
4. Railway определит `Procfile` автоматически
5. Deploy

### Вариант 4: PythonAnywhere (бесплатно, polling)

1. Зарегистрироваться на https://pythonanywhere.com
2. Upload zip архив
3. Открыть Bash console:
   ```bash
   pip install --user python-telegram-bot python-dotenv
   unzip HiWatch_settings_bot.zip -d bot/
   cd bot/
   echo "BOT_TOKEN=твой_токен" > .env
   python bot.py &
   ```
4. Бот работает в фоне (free tier: 3 месяца)

## Команды

- `/start` — приветствие + меню
- `/order` — начать заявку
- `/help` — помощь
- `/id` — узнать свой chat_id
- `/setadmin` — привязать менеджера (только для админов)
- `/cancel` — отменить заявку

## Цены (обновлены 2025)

| Услуга | Цена |
|--------|------|
| Настройка ПК | от 8 000 до 20 000 ₸ |
| Сборка / апгрейд ПК | от 12 000 до 30 000 ₸ |
| ПК + видеонаблюдение | от 15 000 до 35 000 ₸ |
| Консультация | бесплатно |

Выезд по Шымкенту бесплатно. Гарантия 30 дней.

## Архитектура

```
bot.py              — основная версия (python-telegram-bot 21+, async)
simple_bot.py       — синхронная версия (httpx, без зависимостей)
deploy/app.py       — Flask webhook версия (requests + Flask)
```

## Файлы

- `bot.py` — основной бот (async, polling + webhook)
- `simple_bot.py` — упрощённая версия (sync, polling)
- `deploy/app.py` — Flask webhook версия для Render/Koyeb
- `requirements.txt` — зависимости
- `.env.example` — пример конфигурации
- `render.yaml` — конфиг Render
- `koyeb.yaml` — конфиг Koyeb
- `Dockerfile` — Docker образ
- `Procfile` — для Railway/Heroku

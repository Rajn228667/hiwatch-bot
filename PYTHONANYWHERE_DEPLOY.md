# Деплой HiWatch Bot на PythonAnywhere (бесплатно 24/7)

## Что нужно
- Аккаунт на https://www.pythonanywhere.com (free tier)
- GitHub репозиторий: https://github.com/Rajn228667/hiwatch-bot

## Шаг 1: Регистрация
1. Зайди на https://www.pythonanywhere.com/registration/register/beginner/
2. Создай бесплатный аккаунт (Beginner plan)
3. Username будет частью URL: `твой_username.pythonanywhere.com`

## Шаг 2: Клонирование репозитория
1. Открой **Bash console** (вкладка Consoles → Bash)
2. Выполни:
```bash
git clone https://github.com/Rajn228667/hiwatch-bot.git ~/hiwatch-bot
cd ~/hiwatch-bot
pip install --user -r requirements.txt
```

## Шаг 3: Создание .env
В Bash console:
```bash
cat > ~/hiwatch-bot/.env << 'EOF'
BOT_TOKEN=8754883637:AAE4zv8OeejJKuWfBvp7leK4OE3B2SH09DE
ADMIN_USERNAMES=STPierce,Who_Knyaz
ADMIN_CHAT_IDS=1930108146
HIKMART_API_URL=https://hikmart.vercel.app
HIKMART_BOT_TOKEN=hikmart-bot-sync-2025
WEBHOOK_URL=https://ТВОЙ_USERNAME.pythonanywhere.com
EOF
```
Замени `ТВОЙ_USERNAME` на твой username на PythonAnywhere!

## Шаг 4: Создание Web App
1. Перейди на вкладку **Web**
2. Нажми **Add a new web app**
3. Выбери **Manual configuration** → **Python 3.10** (или 3.11/3.12)
4. В разделе **Code** → **WSGI configuration file** нажми на ссылку
5. Откроется редактор. Замени ВСЁ содержимое на:
```python
import sys
sys.path.insert(0, "/home/ТВОЙ_USERNAME/hiwatch-bot")

from wsgi import application as application  # noqa
```
Замени `ТВОЙ_USERNAME` на свой username!

6. Сохрани файл

## Шаг 5: Настройка Virtual Environment
В разделе **Virtualenv** на вкладке Web:
1. Нажми **Enter virtualenv path**
2. Введи: `/home/ТВОЙ_USERNAME/.local` (где установились пакеты через `pip install --user`)

Или создай отдельный venv:
```bash
python -m venv ~/venv
source ~/venv/bin/activate
pip install -r ~/hiwatch-bot/requirements.txt
```
И укажи путь `/home/ТВОЙ_USERNAME/venv` в настройках.

## Шаг 6: Перезагрузка и проверка
1. На вкладке **Web** нажми зелёную кнопку **Reload**
2. Открой в браузере: `https://ТВОЙ_USERNAME.pythonanywhere.com/`
   - Должна быть ошибка 404 или пустая страница (это нормально — бот слушает только `/<BOT_TOKEN>`)
3. Напиши боту в Telegram: `/start`
   - Бот должен ответить!

## Шаг 7: Проверка webhook
В Bash console:
```bash
curl -s "https://api.telegram.org/bot8754883637:AAE4zv8OeejJKuWfBvp7leK4OE3B2SH09DE/getWebhookInfo" | python -m json.tool
```
Должен показать `url: "https://ТВОЙ_USERNAME.pythonanywhere.com/875488..."` и `last_error_message: null`

## Ограничения Free Tier
- **CPU seconds**: 100 секунд в день (хватит для бота — он почти не использует CPU)
- **External internet access**: есть (нужно для Telegram API)
- **Web app**: 1 приложение на `твой_username.pythonanywhere.com`
- **HTTPS**: включён (нужен для webhook)

## Если бот не отвечает
1. Проверь логи: вкладка **Web** → **Log files** → **Error log**
2. Проверь что .env создан правильно
3. Проверь что WSGI файл указывает на правильный путь
4. Reload web app после любых изменений
5. Проверь webhook: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

## Обновление бота
```bash
cd ~/hiwatch-bot
git pull
```
Затем Reload на вкладке Web.

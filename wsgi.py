"""
WSGI entry point for PythonAnywhere deployment.

PythonAnywhere doesn't allow binding to ports, so we use
python-telegram-bot's built-in WSGI integration for webhook mode.

Setup on PythonAnywhere:
1. Go to Web tab → Add a new web app → Manual config → Python 3.10+
2. Set WSGI configuration file to point to this file
3. Set environment variables in /home/USERNAME/.env or PythonAnywhere dashboard
4. Set webhook URL: https://USERNAME.pythonanywhere.com/<BOT_TOKEN>
5. Reload web app

The webhook is automatically set on first request to /.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add this directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env", encoding="utf-8-sig")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().strip('"').strip("'")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment variables")

# Build the Telegram bot application (shared with bot.py)
from bot import build_application

_application = build_application()

# Set webhook on startup
async def _set_webhook():
    if WEBHOOK_URL:
        webhook_endpoint = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await _application.bot.set_webhook(url=webhook_endpoint)
        print(f"✅ Webhook set: {webhook_endpoint}")

# Run webhook setup in async context
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(_set_webhook())
loop.close()

# Create WSGI app — python-telegram-bot provides this
# Each HTTP request to /<BOT_TOKEN> is processed as a Telegram update
application = _application.make_wsgi_app()

# For PythonAnywhere WSGI — they look for `application` variable
app = application

"""
WSGI entry point for PythonAnywhere deployment.
Uses python-telegram-bot webhook via WSGI.
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

# Build the Telegram bot application
from bot import build_application

_application = build_application()

# Set webhook on startup
async def _set_webhook():
    if WEBHOOK_URL:
        webhook_endpoint = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await _application.bot.set_webhook(url=webhook_endpoint)
        print(f"Webhook set: {webhook_endpoint}")
    else:
        print("WARNING: WEBHOOK_URL not set, webhook will not work!")

# Run webhook setup
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_set_webhook())
    loop.close()
except Exception as e:
    print(f"Webhook setup error: {e}")

# Create WSGI app
application = _application.make_wsgi_app()

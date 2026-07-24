"""
WSGI entry point for PythonAnywhere deployment.
Manually processes Telegram updates via WSGI.
"""
import os
import sys
import json
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

# Initialize the application (needed before processing updates)
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

async def _init():
    await _application.initialize()
    if WEBHOOK_URL:
        webhook_endpoint = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        await _application.bot.set_webhook(url=webhook_endpoint)
        print(f"Webhook set: {webhook_endpoint}")

try:
    _loop.run_until_complete(_init())
except Exception as e:
    print(f"Init error: {e}")

# Keep the loop running for async processing
_loop_running = True


def application(environ, start_response):
    """Simple WSGI handler — processes Telegram updates."""
    path_info = environ.get("PATH_INFO", "")
    request_method = environ.get("REQUEST_METHOD", "")

    # Health check
    if request_method == "GET":
        body = b"OK"
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [body]

    # Only process POST to /<BOT_TOKEN>
    if request_method != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"Method Not Allowed"]

    # Read request body
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0))
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else b""
        data = json.loads(body.decode("utf-8"))
    except Exception as e:
        print(f"Parse error: {e}")
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"Bad Request"]

    # Process the update
    try:
        from telegram import Update
        update = Update.de_json(data, _application.bot)
        # Run process_update in the event loop
        _loop.run_until_complete(_application.process_update(update))
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"ok":true}']
    except Exception as e:
        print(f"Process error: {e}")
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"ok":true}']  # Always return 200 to Telegram

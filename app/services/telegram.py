import requests

from app.core.config import get_settings


settings = get_settings()


def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        # Do not crash the app for notification failures
        pass


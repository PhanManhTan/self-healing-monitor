import logging

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


logger = logging.getLogger(__name__)


def send_message(message: str) -> bool:
    """Send a plain-text Telegram message."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram: missing bot token or chat ID")
        return False

    # The number before ':' is the bot ID, not the destination chat ID.
    bot_id = TELEGRAM_BOT_TOKEN.split(":", 1)[0]
    if TELEGRAM_CHAT_ID == bot_id:
        logger.error("Telegram: chat ID is the bot ID; use a user/group chat ID")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    try:
        response = requests.post(url, json=payload, timeout=5)
        data = response.json()
    except requests.RequestException as error:
        logger.error("Telegram connection error: %s", error)
        return False
    except ValueError:
        logger.error("Telegram returned an invalid response (HTTP %s)", response.status_code)
        return False

    if not data.get("ok"):
        description = data.get("description", "Unknown Telegram error")
        logger.error("Telegram HTTP %s: %s", response.status_code, description)
        return False

    return True

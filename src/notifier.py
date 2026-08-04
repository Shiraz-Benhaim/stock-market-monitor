import requests

from config import Config


def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    """Sends a formatted alert message to a Telegram channel/chat."""

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, json=payload)
    return response.status_code == Config.SUCCESS_HTTP_STATUS_CODE

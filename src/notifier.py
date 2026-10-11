import requests

<<<<<<< Updated upstream
from config import Config
=======
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
REQUEST_TIMEOUT_SECONDS = 10
>>>>>>> Stashed changes


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

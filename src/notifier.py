import requests

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
REQUEST_TIMEOUT_SECONDS = 10


def split_message(
    sections: list[str],
    separator: str,
    max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH,
) -> list[str]:
    """Join sections into as few messages as possible, each within `max_length`.

    Sections are never split, so a single section longer than `max_length`
    is sent as its own message.
    """
    messages: list[str] = []
    current = ""
    for section in sections:
        candidate = f"{current}{separator}{section}" if current else section
        if current and len(candidate) > max_length:
            messages.append(current)
            current = section
        else:
            current = candidate

    if current:
        messages.append(current)
    return messages


def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    """Send an HTML-formatted message to a Telegram chat.

    Raises requests.HTTPError if Telegram rejects the message.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

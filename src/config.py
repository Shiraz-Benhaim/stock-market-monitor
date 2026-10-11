import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_HISTORY_PERIOD = "1y"


def parse_symbols(raw_symbols: str) -> tuple[str, ...]:
    """Split a comma-separated symbol list, dropping blanks and normalizing case."""
    return tuple(
        symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()
    )


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    symbols: tuple[str, ...]
    history_period: str = DEFAULT_HISTORY_PERIOD

    @classmethod
    def from_env(cls) -> "Config":
        """Build the configuration from environment variables (and `.env` locally).

        Raises ValueError if the Telegram credentials or SYMBOLS are missing.
        """
        load_dotenv()

        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not telegram_bot_token or not telegram_chat_id:
            raise ValueError(
                "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID "
                "in environment variables."
            )

        symbols = parse_symbols(os.getenv("SYMBOLS", ""))
        if not symbols:
            raise ValueError("Missing SYMBOLS in environment variables.")

        return cls(
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            symbols=symbols,
            history_period=os.getenv("HISTORY_PERIOD") or DEFAULT_HISTORY_PERIOD,
        )

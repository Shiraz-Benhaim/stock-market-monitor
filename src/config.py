import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    SYMBOLS = [symbol.strip() for symbol in os.getenv("SYMBOLS", "AAPL,MSFT,NVDA,QQQ,SPY").split(",")]

    SUCCESS_HTTP_STATUS_CODE = 200
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment variables.")

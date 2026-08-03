import yfinance as yf
import pandas as pd

from config import Config


def fetch_market_history(symbol: str) -> pd.DataFrame:
    """Fetches historical daily market data for a given symbol."""

    ticker = yf.Ticker(symbol)
    market_history = ticker.history(period=Config.HISTORY_PERIOD)
    return market_history

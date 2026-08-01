import yfinance as yf
import pandas as pd


def fetch_market_history(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetches historical daily market data for a given symbol."""

    ticker = yf.Ticker(symbol)
    market_history = ticker.history(period=period)
    return market_history

import yfinance as yf
import pandas as pd


def fetch_market_data(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetches historical daily market data for a given symbol."""

    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    return df

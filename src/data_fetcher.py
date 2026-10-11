import pandas as pd
import yfinance as yf


def fetch_market_history(symbol: str, period: str) -> pd.DataFrame:
    """Fetch historical daily market data for a symbol over a yfinance period."""
    return yf.Ticker(symbol).history(period=period)

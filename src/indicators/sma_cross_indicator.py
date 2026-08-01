import pandas as pd

from src.indicators.base import BaseIndicator


class SMACrossIndicator(BaseIndicator):
    """Triggers an alert if the latest price crosses or falls below a Simple Moving Average (SMA)."""
    
    def __init__(self, window: int = 20, threshold_pct: float = 0.0):
        self.window = window
        self.threshold_pct = threshold_pct

    def evaluate(self, df: pd.DataFrame) -> dict | None:
        if len(df) < self.window:
            return None
        
        df['SMA'] = df['Close'].rolling(window=self.window).mean()
        latest_price = df['Close'].iloc[-1]
        latest_sma = df['SMA'].iloc[-1]
        
        target_sma = latest_sma * (1 - self.threshold_pct)
        if latest_price <= target_sma:
            diff_pct = ((latest_price - latest_sma) / latest_sma) * 100
            return {
                "indicator": f"SMA_{self.window}",
                "latest_price": round(float(latest_price), 2),
                "sma_value": round(float(latest_sma), 2),
                "diff_pct": round(float(diff_pct), 2),
                "message": f"Price (${latest_price:.2f}) is below SMA_{self.window} (${latest_sma:.2f}) by {abs(diff_pct):.2f}%"
            }

        return None

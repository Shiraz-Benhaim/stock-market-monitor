import pandas as pd

from src.indicators.base import IndicatorBase


class SMACrossIndicator(IndicatorBase):
    """Triggers an alert if the latest price crosses or falls below a Simple Moving Average (SMA)."""
    
    def __init__(self, window: int = 20, threshold_percentage: float = 0.0):
        self.window = window
        self.threshold_percentage = threshold_percentage

    def evaluate(self, market_history: pd.DataFrame) -> dict | None:
        if len(market_history) < self.window:
            return None
        
        market_history['SMA'] = market_history['Close'].rolling(window=self.window).mean()
        latest_price = market_history['Close'].iloc[-1]
        latest_sma = market_history['SMA'].iloc[-1]
        
        target_sma = latest_sma * (1 - self.threshold_percentage)
        if latest_price <= target_sma:
            diff_percentage = ((latest_price - latest_sma) / latest_sma) * 100

            return {
                "indicator": f"SMA_{self.window}",
                "latest_price": round(float(latest_price), 2),
                "sma_value": round(float(latest_sma), 2),
                "diff_percentage": round(float(diff_percentage), 2),
                "message": f"Price (${latest_price:.2f}) is below SMA_{self.window} (${latest_sma:.2f}) by {abs(diff_percentage):.2f}%"
            }

        return None

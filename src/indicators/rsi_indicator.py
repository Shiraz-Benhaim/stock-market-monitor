import pandas as pd

from src.indicators.base import IndicatorBase


class RSIIndicator(IndicatorBase):
    """Triggers an alert if RSI is below oversold or above overbought thresholds."""
    
    def __init__(self, period: int = 14, oversold: float = 30.0):
        self.period = period
        self.oversold = oversold

    def evaluate(self, market_history: pd.DataFrame) -> dict | None:
        if len(market_history) < self.period + 1:
            return None
            
        delta = market_history['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi <= self.oversold:
            return {
                "indicator": f"RSI_{self.period}",
                "latest_price": round(float(market_history['Close'].iloc[-1]), 2),
                "rsi_value": round(float(latest_rsi), 2),
                "message": f"RSI is oversold at {latest_rsi:.2f} (Threshold: {self.oversold})"
            }
        return None

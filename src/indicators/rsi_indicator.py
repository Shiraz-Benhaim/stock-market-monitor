import pandas as pd

from src.indicators.base import IndicatorBase, IndicatorResult


class RSIIndicator(IndicatorBase):
    """Trigger an alert if RSI is at or below the oversold threshold.

    Uses Wilder's smoothing, so values match common charting platforms.
    """

    def __init__(self, period: int = 14, oversold: float = 30.0):
        self.period = period
        self.oversold = oversold

    @property
    def min_history(self) -> int:
        return self.period + 1

    def evaluate(self, market_history: pd.DataFrame) -> IndicatorResult | None:
        if len(market_history) < self.min_history:
            return None

        closes = market_history["Close"]
        delta = closes.diff()
        alpha = 1 / self.period
        average_gain = delta.clip(lower=0).ewm(alpha=alpha, adjust=False).mean()
        average_loss = (-delta.clip(upper=0)).ewm(alpha=alpha, adjust=False).mean()

        rsi = 100 - 100 / (1 + average_gain / average_loss)
        latest_rsi = rsi.iloc[-1]

        # Flat prices give 0 / 0 = NaN: there is no meaningful RSI to report.
        if pd.isna(latest_rsi) or latest_rsi > self.oversold:
            return None

        return IndicatorResult(
            indicator=f"RSI_{self.period}",
            message=(
                f"RSI is oversold at {latest_rsi:.2f} (Threshold: {self.oversold})"
            ),
            details={
                "latest_price": round(float(closes.iloc[-1]), 2),
                "rsi_value": round(float(latest_rsi), 2),
            },
        )

import pandas as pd

from src.indicators.base import IndicatorBase, IndicatorResult


class PriceBelowSMAIndicator(IndicatorBase):
    """Trigger an alert if the latest close is below a Simple Moving Average (SMA).

    This is a level check, not a cross: it fires on every run while the price
    stays below the SMA. `threshold_percentage` is a fraction (0.05 = 5%) the
    price must be below the SMA by.
    """

    def __init__(self, window: int = 20, threshold_percentage: float = 0.0):
        self.window = window
        self.threshold_percentage = threshold_percentage

    @property
    def min_history(self) -> int:
        return self.window

    def evaluate(self, market_history: pd.DataFrame) -> IndicatorResult | None:
        if len(market_history) < self.min_history:
            return None

        closes = market_history["Close"]
        latest_price = float(closes.iloc[-1])
        latest_sma = float(closes.rolling(window=self.window).mean().iloc[-1])

        if latest_price > latest_sma * (1 - self.threshold_percentage):
            return None

        diff_percentage = (latest_price - latest_sma) / latest_sma * 100
        return IndicatorResult(
            indicator=f"SMA_{self.window}",
            message=(
                f"Price (${latest_price:.2f}) is below SMA_{self.window} "
                f"(${latest_sma:.2f}) by {abs(diff_percentage):.2f}%"
            ),
            details={
                "latest_price": round(latest_price, 2),
                "sma_value": round(latest_sma, 2),
                "diff_percentage": round(diff_percentage, 2),
            },
        )

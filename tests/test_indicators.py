import pandas as pd
import pytest

from src.indicators import IndicatorResult, PriceBelowSMAIndicator, RSIIndicator


def make_history(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": closes})


class TestPriceBelowSMAIndicator:
    def test_triggers_when_price_below_sma(self):
        history = make_history([10.0] * 19 + [5.0])

        result = PriceBelowSMAIndicator(window=20).evaluate(history)

        assert isinstance(result, IndicatorResult)
        assert result.indicator == "SMA_20"
        assert result.details["sma_value"] == 9.75
        assert result.details["diff_percentage"] == pytest.approx(-48.72)

    def test_does_not_trigger_when_price_above_sma(self):
        history = make_history([10.0] * 19 + [15.0])

        assert PriceBelowSMAIndicator(window=20).evaluate(history) is None

    def test_threshold_requires_price_further_below(self):
        # SMA = 9.99, price is ~1.9% below it: under a 5% threshold.
        history = make_history([10.0] * 19 + [9.8])

        indicator = PriceBelowSMAIndicator(window=20, threshold_percentage=0.05)
        assert indicator.evaluate(history) is None

    def test_returns_none_without_enough_history(self):
        history = make_history([10.0] * 19)

        assert PriceBelowSMAIndicator(window=20).evaluate(history) is None

    def test_does_not_modify_market_history(self):
        history = make_history([10.0] * 19 + [5.0])

        PriceBelowSMAIndicator(window=20).evaluate(history)

        assert list(history.columns) == ["Close"]


class TestRSIIndicator:
    def test_triggers_on_steady_decline(self):
        history = make_history([100.0 - i for i in range(30)])

        result = RSIIndicator(period=14, oversold=30.0).evaluate(history)

        assert result is not None
        assert result.indicator == "RSI_14"
        assert result.details["rsi_value"] == 0.0

    def test_does_not_trigger_on_steady_rise(self):
        history = make_history([100.0 + i for i in range(30)])

        assert RSIIndicator(period=14).evaluate(history) is None

    def test_flat_prices_do_not_trigger(self):
        history = make_history([100.0] * 30)

        assert RSIIndicator(period=14).evaluate(history) is None

    def test_returns_none_without_enough_history(self):
        history = make_history([100.0 - i for i in range(14)])

        assert RSIIndicator(period=14).evaluate(history) is None

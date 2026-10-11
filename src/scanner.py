import logging

import pandas as pd

from src.indicators import IndicatorBase, IndicatorResult

logger = logging.getLogger(__name__)


def scan_symbol(
    symbol: str,
    market_history: pd.DataFrame,
    indicators: list[IndicatorBase],
) -> list[IndicatorResult]:
    results: list[IndicatorResult] = []

    for indicator in indicators:
        if len(market_history) < indicator.min_history:
            logger.warning(
                "%s: only %d rows of history, %s needs %d; skipping it",
                symbol,
                len(market_history),
                type(indicator).__name__,
                indicator.min_history,
            )
            continue

        result = indicator.evaluate(market_history)
        if result is not None:
            results.append(result)

    return results

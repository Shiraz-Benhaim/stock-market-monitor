from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class IndicatorResult:
    """A triggered indicator: a short name, a human-readable message, and values."""

    indicator: str
    message: str
    details: dict[str, float] = field(default_factory=dict)


class IndicatorBase(ABC):
    """Abstract Base Class for all technical indicators."""

    @property
    @abstractmethod
    def min_history(self) -> int:
        """Return the minimum number of rows `evaluate` needs to produce a result."""

    @abstractmethod
    def evaluate(self, market_history: pd.DataFrame) -> IndicatorResult | None:
        """Evaluate the indicator conditions on historical market data.

        Return an IndicatorResult if triggered, otherwise None. Must not
        modify `market_history`, which is shared between indicators.
        """

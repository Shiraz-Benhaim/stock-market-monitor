from abc import ABC, abstractmethod

import pandas as pd


class IndicatorBase(ABC):
    """Abstract Base Class for all technical indicators."""
    
    @abstractmethod
    def evaluate(self, market_history: pd.DataFrame) -> dict | None:
        """
        Evaluates indicator conditions on the historical market data.
        Returns a dict with alert details if triggered, otherwise None.
        """

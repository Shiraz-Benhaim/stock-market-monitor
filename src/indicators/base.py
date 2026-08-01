from abc import ABC, abstractmethod

import pandas as pd


class BaseIndicator(ABC):
    """Abstract Base Class for all technical indicators."""
    
    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> dict | None:
        """
        Evaluates indicator conditions on the historical market data.
        Returns a dict with alert details if triggered, otherwise None.
        """

from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    name = "BASE"

    @abstractmethod
    def generate_signal(self, candles):
        """
        candles: list of last N candles (dict)
        return: BUY / SELL / HOLD
        """
        pass

import pandas as pd

class EMACrossoverStrategy:

    name = "EMA_CROSSOVER"

    def __init__(self, fast=9, slow=21):
        self.fast = fast
        self.slow = slow

    def generate_signal(self, candles: pd.DataFrame):
        """
        candles columns:
        candle_time, open, high, low, close, volume
        """

        if len(candles) < self.slow:
            return None

        candles["ema_fast"] = candles["close"].ewm(span=self.fast).mean()
        candles["ema_slow"] = candles["close"].ewm(span=self.slow).mean()

        last = candles.iloc[-1]
        prev = candles.iloc[-2]

        if prev.ema_fast <= prev.ema_slow and last.ema_fast > last.ema_slow:
            return "BUY"

        if prev.ema_fast >= prev.ema_slow and last.ema_fast < last.ema_slow:
            return "SELL"

        return "HOLD"

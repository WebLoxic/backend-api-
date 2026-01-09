import json
from app.mtf_config import MTF_MAP

class MTFAggregator:
    def __init__(self, redis):
        self.redis = redis
        self.cache = {}  # {(token, tf): candle}

    def process_1m_candle(self, token: int, candle_1m: dict):
        base_time = candle_1m["time"]  # epoch seconds (minute start)

        for tf, size in MTF_MAP.items():
            bucket = base_time - (base_time % (size * 60))
            key = (token, tf)

            c = self.cache.get(key)

            if not c or c["time"] != bucket:
                # 🔴 close old candle
                if c:
                    self.publish(token, tf, c)

                # 🟢 new candle
                c = {
                    "time": bucket,
                    "open": candle_1m["open"],
                    "high": candle_1m["high"],
                    "low": candle_1m["low"],
                    "close": candle_1m["close"],
                    "volume": candle_1m.get("volume", 0),
                }
                self.cache[key] = c
            else:
                # 🔁 update
                c["high"] = max(c["high"], candle_1m["high"])
                c["low"] = min(c["low"], candle_1m["low"])
                c["close"] = candle_1m["close"]
                c["volume"] += candle_1m.get("volume", 0)

    def publish(self, token, tf, candle):
        stream = f"candle_stream:{token}:{tf}"
        self.redis.xadd(stream, candle)

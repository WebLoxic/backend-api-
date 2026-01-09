import json
import logging
from app.services.live_mtf_config import LIVE_MTF

log = logging.getLogger("live_mtf")

class LiveMTFAggregator:
    def __init__(self, redis):
        self.redis = redis
        self.cache = {}   # (token, tf) → candle

    def process_1m_close(self, token: int, candle_1m: dict):
        base_time = candle_1m["time"]  # epoch (minute open)

        for tf, size in LIVE_MTF.items():
            tf_sec = size * 60
            bucket = base_time - (base_time % tf_sec)
            key = (token, tf)

            c = self.cache.get(key)

            # 🔴 NEW BUCKET
            if not c or c["time"] != bucket:
                if c:
                    self.publish(token, tf, c)

                c = {
                    "time": bucket,
                    "open": candle_1m["open"],
                    "high": candle_1m["high"],
                    "low": candle_1m["low"],
                    "close": candle_1m["close"],
                    "volume": candle_1m.get("volume", 0),
                }
                self.cache[key] = c

            # 🔁 UPDATE
            else:
                c["high"] = max(c["high"], candle_1m["high"])
                c["low"] = min(c["low"], candle_1m["low"])
                c["close"] = candle_1m["close"]
                c["volume"] += candle_1m.get("volume", 0)

    def publish(self, token, tf, candle):
        stream = f"candle_stream:{token}:{tf}"
        self.redis.xadd(stream, candle)
        log.info(f"🕯️ LIVE {tf} CLOSE | token={token} | time={candle['time']}")

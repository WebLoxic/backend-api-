import redis
import logging
from app.services.live_mtf_aggregator import LiveMTFAggregator

logging.basicConfig(level=logging.INFO)

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
agg = LiveMTFAggregator(r)

last_id = "$"

STREAM_PATTERN = "candle_stream:*:1m"

print("🟢 LIVE MTF RUNNER STARTED")

while True:
    res = r.xread({STREAM_PATTERN: last_id}, block=0, count=10)

    for stream, msgs in res:
        token = int(stream.split(":")[1])

        for msg_id, data in msgs:
            last_id = msg_id

            candle_1m = {
                "time": int(data["time"]),
                "open": float(data["open"]),
                "high": float(data["high"]),
                "low": float(data["low"]),
                "close": float(data["close"]),
                "volume": float(data.get("volume", 0)),
            }

            agg.process_1m_close(token, candle_1m)

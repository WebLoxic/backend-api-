import redis
from app.mtf_aggregator import MTFAggregator

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
agg = MTFAggregator(r)

STREAM_PATTERN = "candle_stream:*:1m"

last_id = "$"

while True:
    res = r.xread({STREAM_PATTERN: last_id}, block=1000)
    for stream, msgs in res:
        for msg_id, data in msgs:
            last_id = msg_id

            token = int(stream.split(":")[1])
            candle = {
                "time": int(data["time"]),
                "open": float(data["open"]),
                "high": float(data["high"]),
                "low": float(data["low"]),
                "close": float(data["close"]),
                "volume": float(data.get("volume", 0)),
            }

            agg.process_1m_candle(token, candle)

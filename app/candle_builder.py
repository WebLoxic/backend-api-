

# import json
# import time
# import logging
# import redis
# from sqlalchemy import text
# from zoneinfo import ZoneInfo
# from datetime import datetime

# from app.db import SessionLocal

# log = logging.getLogger("candle_builder")

# # =========================
# # CONFIG
# # =========================
# IST = ZoneInfo("Asia/Kolkata")
# INTERVAL = 60  # 1 minute

# r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# CANDLES = {}          # token -> candle
# LAST_VOL = {}         # token -> last cumulative volume

# # =========================
# def floor_minute(ts: datetime) -> int:
#     return int(ts.replace(second=0, microsecond=0).timestamp())

# def market_open(ts: datetime) -> bool:
#     m = ts.hour * 60 + ts.minute
#     return 555 <= m <= 930   # 09:15–15:30 IST

# # =========================
# def build_candles():
#     log.info("🕯️ Zerodha-style Candle Builder started")

#     while True:
#         keys = r.keys("tick:*")

#         for key in keys:
#             raw = r.get(key)
#             if not raw:
#                 continue

#             try:
#                 tick = json.loads(raw)
#             except Exception:
#                 continue

#             token = tick.get("instrument_token")
#             ltp = tick.get("ltp")
#             exch_ts = tick.get("exchange_timestamp")

#             if not token or not ltp or not exch_ts:
#                 continue

#             ts = datetime.fromisoformat(exch_ts).astimezone(IST)

#             # ✅ strict market hours
#             if not market_open(ts):
#                 continue

#             ct = floor_minute(ts)

#             # ===== volume handling (delta) =====
#             cum_vol = tick.get("volume_traded_today", 0)
#             prev_vol = LAST_VOL.get(token, cum_vol)
#             delta_vol = max(cum_vol - prev_vol, 0)
#             LAST_VOL[token] = cum_vol

#             c = CANDLES.get(token)

#             # ===== NEW CANDLE =====
#             if not c or c["candle_time"] != ct:
#                 if c:
#                     save_candle(token, c)

#                 CANDLES[token] = {
#                     "candle_time": ct,
#                     "open": ltp,
#                     "high": ltp,
#                     "low": ltp,
#                     "close": ltp,
#                     "volume": delta_vol,
#                 }

#             # ===== UPDATE =====
#             else:
#                 c["high"] = max(c["high"], ltp)
#                 c["low"]  = min(c["low"], ltp)
#                 c["close"] = ltp
#                 c["volume"] += delta_vol

#         time.sleep(0.5)

# # =========================
# def save_candle(token: int, c: dict):
#     db = SessionLocal()
#     try:
#         db.execute(
#             text("""
#                 INSERT INTO zerodha_candles_1m
#                 (instrument_token, candle_time, open, high, low, close, volume)
#                 VALUES
#                 (:t, to_timestamp(:ct), :o, :h, :l, :c, :v)
#                 ON CONFLICT (instrument_token, candle_time) DO NOTHING
#             """),
#             {
#                 "t": token,
#                 "ct": c["candle_time"],
#                 "o": c["open"],
#                 "h": c["high"],
#                 "l": c["low"],
#                 "c": c["close"],
#                 "v": c["volume"],
#             }
#         )
#         db.commit()

#         log.info(
#             "🕯️ saved %s @ %s",
#             token,
#             datetime.fromtimestamp(c["candle_time"], IST)
#         )

#     finally:
#         db.close()

# # =========================
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     build_candles()












# # candle_builder.py

# import json
# import time
# import logging
# import redis
# from datetime import datetime, timezone
# from zoneinfo import ZoneInfo

# from sqlalchemy import text
# from app.db import SessionLocal

# log = logging.getLogger("candle_builder")

# # =========================
# # CONFIG
# # =========================
# IST = ZoneInfo("Asia/Kolkata")
# INTERVAL = 60  # 1 minute candles

# REDIS_HOST = "localhost"
# REDIS_PORT = 6379

# r = redis.Redis(
#     host=REDIS_HOST,
#     port=REDIS_PORT,
#     decode_responses=True
# )

# # =========================
# # IN-MEMORY STATE
# # =========================
# CANDLES = {}        # token -> active candle
# LAST_VOLUME = {}   # token -> last cumulative volume


# # =========================
# # SAFE TIMESTAMP PARSER
# # =========================
# def parse_exchange_ts(exch_ts):
#     """
#     Always return timezone-aware IST datetime
#     Handles:
#     - ISO string
#     - epoch seconds
#     - datetime object
#     Windows-safe
#     """
#     if exch_ts is None:
#         return None

#     try:
#         # ISO string
#         if isinstance(exch_ts, str):
#             ts = datetime.fromisoformat(exch_ts)

#         # epoch seconds
#         elif isinstance(exch_ts, (int, float)):
#             ts = datetime.fromtimestamp(exch_ts, tz=timezone.utc)

#         # datetime object
#         elif isinstance(exch_ts, datetime):
#             ts = exch_ts

#         else:
#             return None

#         # make timezone-aware if naive
#         if ts.tzinfo is None:
#             ts = ts.replace(tzinfo=timezone.utc)

#         return ts.astimezone(IST)

#     except Exception:
#         return None


# # =========================
# # HELPERS
# # =========================
# def floor_minute(ts: datetime) -> int:
#     """
#     Candle open time (epoch seconds)
#     """
#     ts = ts.replace(second=0, microsecond=0)
#     return int(ts.timestamp())


# def market_open(ts: datetime) -> bool:
#     """
#     NSE market hours: 09:15–15:30 IST
#     """
#     m = ts.hour * 60 + ts.minute
#     return 555 <= m <= 930


# # =========================
# # CORE LOOP
# # =========================
# def build_candles():
#     log.info("🕯️ Zerodha-style Candle Builder STARTED")

#     while True:
#         try:
#             for key in r.scan_iter("tick:*"):
#                 raw = r.get(key)
#                 if not raw:
#                     continue

#                 try:
#                     tick = json.loads(raw)
#                 except Exception:
#                     continue

#                 token = tick.get("instrument_token")
#                 price = tick.get("last_price")
#                 exch_ts = tick.get("exchange_timestamp")
#                 cum_vol = tick.get("volume_traded")

#                 # mandatory fields
#                 if token is None or price is None or exch_ts is None:
#                     continue

#                 # SAFE exchange time
#                 ts = parse_exchange_ts(exch_ts)
#                 if ts is None:
#                     continue

#                 if not market_open(ts):
#                     continue

#                 candle_time = floor_minute(ts)

#                 # -------------------------
#                 # VOLUME (SAFE)
#                 # -------------------------
#                 if cum_vol is None:
#                     cum_vol = 0

#                 prev_vol = LAST_VOLUME.get(token)
#                 if prev_vol is None:
#                     delta_vol = 0
#                 else:
#                     delta_vol = max(cum_vol - prev_vol, 0)

#                 LAST_VOLUME[token] = cum_vol

#                 candle = CANDLES.get(token)

#                 # -------------------------
#                 # NEW CANDLE
#                 # -------------------------
#                 if not candle or candle["time"] != candle_time:
#                     if candle:
#                         save_candle(token, candle)
#                         publish_candle(token, candle)

#                     CANDLES[token] = {
#                         "time": candle_time,
#                         "open": price,
#                         "high": price,
#                         "low": price,
#                         "close": price,
#                         "volume": delta_vol,
#                     }

#                 # -------------------------
#                 # UPDATE CANDLE
#                 # -------------------------
#                 else:
#                     candle["high"] = max(candle["high"], price)
#                     candle["low"] = min(candle["low"], price)
#                     candle["close"] = price
#                     candle["volume"] += delta_vol

#             time.sleep(0.2)  # real-time safe

#         except Exception as e:
#             log.exception(f"❌ Candle builder error: {e}")
#             time.sleep(1)


# # =========================
# # SAVE TO DB
# # =========================
# def save_candle(token: int, c: dict):
#     db = SessionLocal()
#     try:
#         db.execute(
#             text("""
#                 INSERT INTO zerodha_candles_1m
#                 (instrument_token, candle_time, open, high, low, close, volume)
#                 VALUES
#                 (:t, to_timestamp(:ct), :o, :h, :l, :c, :v)
#                 ON CONFLICT (instrument_token, candle_time) DO NOTHING
#             """),
#             {
#                 "t": token,
#                 "ct": c["time"],
#                 "o": c["open"],
#                 "h": c["high"],
#                 "l": c["low"],
#                 "c": c["close"],
#                 "v": c["volume"],
#             }
#         )
#         db.commit()

#         log.info(
#             "🕯️ saved candle | token=%s | %s",
#             token,
#             datetime.fromtimestamp(c["time"], IST)
#         )
#     finally:
#         db.close()


# # =========================
# # REDIS PUBLISH (LIVE)
# # =========================
# def publish_candle(token: int, c: dict):
#     payload = {
#         "type": "candle",
#         "token": token,
#         "data": {
#             "time": c["time"],
#             "open": c["open"],
#             "high": c["high"],
#             "low": c["low"],
#             "close": c["close"],
#             "volume": c["volume"],
#         }
#     }

#     r.publish(f"candles:{token}", json.dumps(payload))


# # =========================
# # ENTRYPOINT
# # =========================
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     build_candles()











# # app/candle_builder.py

# import json
# import time
# import logging
# import redis
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from sqlalchemy import text
# from app.db import SessionLocal

# log = logging.getLogger("candle_builder")

# # =========================
# # CONFIG
# # =========================
# IST = ZoneInfo("Asia/Kolkata")
# INTERVAL = 60  # 1 minute candle

# REDIS_HOST = "localhost"   # docker -> "redis"
# REDIS_PORT = 6379

# r = redis.Redis(
#     host=REDIS_HOST,
#     port=REDIS_PORT,
#     decode_responses=True
# )

# # =========================
# # STATE (IN-MEMORY)
# # =========================
# CANDLES = {}        # token -> active candle
# LAST_VOLUME = {}   # token -> last cumulative volume
# STREAM_POS = {}    # token -> last redis stream id
# TOKENS = set()     # active tokens


# # =========================
# # HELPERS
# # =========================
# def floor_minute_epoch(ts: int) -> int:
#     """Return candle open time (epoch seconds)"""
#     return ts - (ts % INTERVAL)


# def market_open(epoch_ts: int) -> bool:
#     """NSE market hours: 09:15–15:30 IST"""
#     ts = datetime.fromtimestamp(epoch_ts, IST)
#     m = ts.hour * 60 + ts.minute
#     return 555 <= m <= 930


# # =========================
# # DB SAVE
# # =========================
# def save_candle(token: int, c: dict):
#     db = SessionLocal()
#     try:
#         db.execute(
#             text("""
#                 INSERT INTO zerodha_candles_1m
#                 (instrument_token, candle_time, open, high, low, close, volume)
#                 VALUES
#                 (:t, to_timestamp(:ct), :o, :h, :l, :c, :v)
#                 ON CONFLICT (instrument_token, candle_time) DO NOTHING
#             """),
#             {
#                 "t": token,
#                 "ct": c["time"],
#                 "o": c["open"],
#                 "h": c["high"],
#                 "l": c["low"],
#                 "c": c["close"],
#                 "v": c["volume"],
#             }
#         )
#         db.commit()

#         log.info(
#             "🕯️ saved candle | token=%s | %s",
#             token,
#             datetime.fromtimestamp(c["time"], IST)
#         )
#     finally:
#         db.close()


# # =========================
# # REDIS PUBLISH (UI)
# # =========================
# def publish_candle(token: int, c: dict):
#     payload = {
#         "time": c["time"],
#         "open": c["open"],
#         "high": c["high"],
#         "low": c["low"],
#         "close": c["close"],
#         "volume": c["volume"],
#     }

#     log.info(f"📤 REDIS PUBLISH candle:{token} → {payload}")

#     r.publish(f"candle:{token}", json.dumps(payload))


# # =========================
# # CORE LOOP (STREAM BASED)
# # =========================
# def build_candles():
#     log.info("🕯️ REAL-TIME Candle Builder STARTED (Redis Streams)")

#     while True:
#         try:
#             # -------------------------------------------------
#             # 1️⃣ DISCOVER STREAMS ONCE (NO CONTINUOUS SCAN)
#             # -------------------------------------------------
#             if not TOKENS:
#                 for key in r.scan_iter("tick_stream:*"):
#                     token = int(key.split(":")[1])
#                     TOKENS.add(token)
#                     STREAM_POS[token] = "$"

#                 if not TOKENS:
#                     time.sleep(0.2)
#                     continue

#             # -------------------------------------------------
#             # 2️⃣ BUILD STREAM MAP (NO SCAN HERE)
#             # -------------------------------------------------
#             streams = {
#                 f"tick_stream:{token}": STREAM_POS[token]
#                 for token in TOKENS
#             }

#             # -------------------------------------------------
#             # 3️⃣ BLOCKING READ (REAL TIME)
#             # -------------------------------------------------
#             data = r.xread(streams, block=0, count=100)

#             for stream, entries in data:
#                 token = int(stream.split(":")[1])

#                 for msg_id, tick in entries:
#                     STREAM_POS[token] = msg_id

#                     ts = int(tick["ts"])            # epoch UTC
#                     price = float(tick["price"])
#                     cum_vol = int(tick.get("volume", 0))

#                     if not market_open(ts):
#                         continue

#                     candle_time = floor_minute_epoch(ts)

#                     # -------------------------
#                     # VOLUME CALC
#                     # -------------------------
#                     prev = LAST_VOLUME.get(token)
#                     delta_vol = 0 if prev is None else max(cum_vol - prev, 0)
#                     LAST_VOLUME[token] = cum_vol

#                     candle = CANDLES.get(token)

#                     # -------------------------
#                     # NEW CANDLE
#                     # -------------------------
#                     if not candle or candle["time"] != candle_time:
#                         if candle:
#                             save_candle(token, candle)
#                             publish_candle(token, candle)

#                         CANDLES[token] = {
#                             "time": candle_time,
#                             "open": price,
#                             "high": price,
#                             "low": price,
#                             "close": price,
#                             "volume": delta_vol,
#                         }

#                     # -------------------------
#                     # UPDATE CANDLE
#                     # -------------------------
#                     else:
#                         candle["high"] = max(candle["high"], price)
#                         candle["low"] = min(candle["low"], price)
#                         candle["close"] = price
#                         candle["volume"] += delta_vol

#         except Exception as e:
#             log.exception(f"❌ Candle builder error: {e}")
#             time.sleep(1)


# # =========================
# # ENTRYPOINT
# # =========================
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     build_candles()








# app/candle_builder.py

import json
import time
import logging
import redis
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from app.db import SessionLocal

log = logging.getLogger("candle_builder")

# =========================
# CONFIG
# =========================
IST = ZoneInfo("Asia/Kolkata")
INTERVAL = 60  # 1 minute candles

REDIS_HOST = "localhost"   # docker: "redis"
REDIS_PORT = 6379

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

# =========================
# STATE (IN-MEMORY)
# =========================
CANDLES = {}        # token -> active candle
LAST_VOLUME = {}   # token -> last cumulative volume
STREAM_POS = {}    # token -> last redis stream id
TOKENS = set()     # active tokens


# =========================
# HELPERS
# =========================
def floor_minute_epoch(ts: int) -> int:
    """Return candle open time (epoch seconds)"""
    return ts - (ts % INTERVAL)


def market_open(epoch_ts: int) -> bool:
    """NSE market hours: 09:15–15:30 IST"""
    ts = datetime.fromtimestamp(epoch_ts, IST)
    m = ts.hour * 60 + ts.minute
    return 555 <= m <= 930


# =========================
# DB SAVE (1m BASE CANDLE)
# =========================
def save_candle(token: int, c: dict):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO zerodha_candles_1m
                (instrument_token, candle_time, open, high, low, close, volume)
                VALUES
                (:t, to_timestamp(:ct), :o, :h, :l, :c, :v)
                ON CONFLICT (instrument_token, candle_time) DO NOTHING
            """),
            {
                "t": token,
                "ct": c["time"],
                "o": c["open"],
                "h": c["high"],
                "l": c["low"],
                "c": c["close"],
                "v": c["volume"],
            }
        )
        db.commit()

        log.info(
            "🕯️ saved 1m candle | token=%s | %s",
            token,
            datetime.fromtimestamp(c["time"], IST)
        )
    finally:
        db.close()


# =========================
# REDIS PUBLISH (UI WS)
# =========================
def publish_candle(token: int, c: dict):
    payload = {
        "time": c["time"],
        "open": c["open"],
        "high": c["high"],
        "low": c["low"],
        "close": c["close"],
        "volume": c["volume"],
    }

    log.info(f"📤 REDIS PUBLISH candle:{token} → {payload}")
    r.publish(f"candle:{token}", json.dumps(payload))


# =========================
# REDIS STREAM (🔥 MTF INPUT)
# =========================
def stream_candle(token: int, c: dict):
    """
    Push CLOSED 1m candle to Redis Stream
    Used by live_mtf_runner
    """
    r.xadd(
        f"candle_stream:{token}:1m",
        {
            "time": c["time"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
        }
    )

    log.info(
        f"📥 STREAM XADD candle_stream:{token}:1m | "
        f"{datetime.fromtimestamp(c['time'], IST)}"
    )


# =========================
# CORE LOOP (REDIS STREAM)
# =========================
def build_candles():
    log.info("🕯️ REAL-TIME Candle Builder STARTED (Redis Streams)")

    while True:
        try:
            # -------------------------------------------------
            # 1️⃣ DISCOVER STREAMS ONCE
            # -------------------------------------------------
            if not TOKENS:
                for key in r.scan_iter("tick_stream:*"):
                    token = int(key.split(":")[1])
                    TOKENS.add(token)
                    STREAM_POS[token] = "$"

                if not TOKENS:
                    time.sleep(0.2)
                    continue

            # -------------------------------------------------
            # 2️⃣ BUILD STREAM MAP
            # -------------------------------------------------
            streams = {
                f"tick_stream:{token}": STREAM_POS[token]
                for token in TOKENS
            }

            # -------------------------------------------------
            # 3️⃣ BLOCKING READ (LIVE)
            # -------------------------------------------------
            data = r.xread(streams, block=0, count=100)

            for stream, entries in data:
                token = int(stream.split(":")[1])

                for msg_id, tick in entries:
                    STREAM_POS[token] = msg_id

                    ts = int(tick["ts"])            # epoch (UTC)
                    price = float(tick["price"])
                    cum_vol = int(tick.get("volume", 0))

                    if not market_open(ts):
                        continue

                    candle_time = floor_minute_epoch(ts)

                    # -------------------------
                    # VOLUME DELTA
                    # -------------------------
                    prev = LAST_VOLUME.get(token)
                    delta_vol = 0 if prev is None else max(cum_vol - prev, 0)
                    LAST_VOLUME[token] = cum_vol

                    candle = CANDLES.get(token)

                    # -------------------------
                    # NEW MINUTE → CLOSE OLD
                    # -------------------------
                    if not candle or candle["time"] != candle_time:
                        if candle:
                            save_candle(token, candle)
                            publish_candle(token, candle)
                            stream_candle(token, candle)   # 🔥 MTF FIX

                        CANDLES[token] = {
                            "time": candle_time,
                            "open": price,
                            "high": price,
                            "low": price,
                            "close": price,
                            "volume": delta_vol,
                        }

                    # -------------------------
                    # UPDATE CURRENT CANDLE
                    # -------------------------
                    else:
                        candle["high"] = max(candle["high"], price)
                        candle["low"] = min(candle["low"], price)
                        candle["close"] = price
                        candle["volume"] += delta_vol

        except Exception as e:
            log.exception(f"❌ Candle builder error: {e}")
            time.sleep(1)


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_candles()

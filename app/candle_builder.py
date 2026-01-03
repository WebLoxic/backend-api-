# # app/candle_builder.py

# import json
# import time
# import logging
# import redis
# from sqlalchemy import text
# from app.db import SessionLocal

# from zoneinfo import ZoneInfo
# from datetime import datetime

# log = logging.getLogger("candle_builder")

# # =========================
# # TIMEZONE & MARKET CONFIG
# # =========================
# IST = ZoneInfo("Asia/Kolkata")
# INTERVAL = 60  # 1-minute candles

# def ist_now():
#     return datetime.now(IST)

# def is_market_open():
#     now = ist_now()
#     mins = now.hour * 60 + now.minute
#     return 555 <= mins <= 930   # 09:15 – 15:30 IST

# def candle_start(ts: int) -> int:
#     return ts - (ts % INTERVAL)

# # =========================
# # REDIS
# # =========================
# r = redis.Redis(
#     host="localhost",
#     port=6379,
#     decode_responses=True
# )

# # in-memory candle buffer
# CANDLES = {}

# # =========================
# # MAIN LOOP
# # =========================
# def build_candles():
#     log.info("🕯️ Candle Builder Started (IST, Zerodha-style)")

#     while True:
#         # ❌ NO candles outside market hours
#         if not is_market_open():
#             time.sleep(5)
#             continue

#         now_ist = ist_now()
#         now_ts = int(now_ist.timestamp())
#         candle_time = candle_start(now_ts)

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
#             price = tick.get("ltp")
#             exch_ts = tick.get("exchange_timestamp")

#             # ❌ invalid tick
#             if not token or not price or not exch_ts:
#                 continue

#             # use ONLY exchange timestamp (IST)
#             tick_ts = int(
#                 datetime.fromisoformat(exch_ts).timestamp()
#             )

#             # safety: ignore stale ticks
#             if abs(tick_ts - now_ts) > 120:
#                 continue

#             ct = candle_start(tick_ts)

#             c = CANDLES.get(token)

#             # =========================
#             # NEW CANDLE
#             # =========================
#             if not c or c["candle_time"] != ct:
#                 if c:
#                     save_candle(token, c)

#                 CANDLES[token] = {
#                     "candle_time": ct,
#                     "open": price,
#                     "high": price,
#                     "low": price,
#                     "close": price,
#                     "volume": tick.get("volume", 0),
#                 }

#             # =========================
#             # UPDATE CANDLE
#             # =========================
#             else:
#                 c["high"] = max(c["high"], price)
#                 c["low"]  = min(c["low"], price)
#                 c["close"] = price
#                 c["volume"] = tick.get("volume", c["volume"])

#         time.sleep(1)

# # =========================
# # SAVE TO DB
# # =========================
# def save_candle(token: int, candle: dict):
#     db = SessionLocal()
#     try:
#         db.execute(
#             text("""
#                 INSERT INTO zerodha_candles_1m
#                 (instrument_token, candle_time, open, high, low, close, volume)
#                 VALUES
#                 (:token, to_timestamp(:ct), :o, :h, :l, :c, :v)
#                 ON CONFLICT (instrument_token, candle_time) DO NOTHING
#             """),
#             {
#                 "token": token,
#                 "ct": candle["candle_time"],
#                 "o": candle["open"],
#                 "h": candle["high"],
#                 "l": candle["low"],
#                 "c": candle["close"],
#                 "v": candle["volume"],
#             }
#         )
#         db.commit()

#         log.info(
#             "🕯️ Candle saved | token=%s time=%s",
#             token,
#             datetime.fromtimestamp(candle["candle_time"], IST)
#         )

#     finally:
#         db.close()

# # =========================
# # ENTRY
# # =========================
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     build_candles()






import json
import time
import logging
import redis
from sqlalchemy import text
from zoneinfo import ZoneInfo
from datetime import datetime

from app.db import SessionLocal

log = logging.getLogger("candle_builder")

# =========================
# CONFIG
# =========================
IST = ZoneInfo("Asia/Kolkata")
INTERVAL = 60  # 1 minute

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

CANDLES = {}          # token -> candle
LAST_VOL = {}         # token -> last cumulative volume

# =========================
def floor_minute(ts: datetime) -> int:
    return int(ts.replace(second=0, microsecond=0).timestamp())

def market_open(ts: datetime) -> bool:
    m = ts.hour * 60 + ts.minute
    return 555 <= m <= 930   # 09:15–15:30 IST

# =========================
def build_candles():
    log.info("🕯️ Zerodha-style Candle Builder started")

    while True:
        keys = r.keys("tick:*")

        for key in keys:
            raw = r.get(key)
            if not raw:
                continue

            try:
                tick = json.loads(raw)
            except Exception:
                continue

            token = tick.get("instrument_token")
            ltp = tick.get("ltp")
            exch_ts = tick.get("exchange_timestamp")

            if not token or not ltp or not exch_ts:
                continue

            ts = datetime.fromisoformat(exch_ts).astimezone(IST)

            # ✅ strict market hours
            if not market_open(ts):
                continue

            ct = floor_minute(ts)

            # ===== volume handling (delta) =====
            cum_vol = tick.get("volume_traded_today", 0)
            prev_vol = LAST_VOL.get(token, cum_vol)
            delta_vol = max(cum_vol - prev_vol, 0)
            LAST_VOL[token] = cum_vol

            c = CANDLES.get(token)

            # ===== NEW CANDLE =====
            if not c or c["candle_time"] != ct:
                if c:
                    save_candle(token, c)

                CANDLES[token] = {
                    "candle_time": ct,
                    "open": ltp,
                    "high": ltp,
                    "low": ltp,
                    "close": ltp,
                    "volume": delta_vol,
                }

            # ===== UPDATE =====
            else:
                c["high"] = max(c["high"], ltp)
                c["low"]  = min(c["low"], ltp)
                c["close"] = ltp
                c["volume"] += delta_vol

        time.sleep(0.5)

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
                "ct": c["candle_time"],
                "o": c["open"],
                "h": c["high"],
                "l": c["low"],
                "c": c["close"],
                "v": c["volume"],
            }
        )
        db.commit()

        log.info(
            "🕯️ saved %s @ %s",
            token,
            datetime.fromtimestamp(c["candle_time"], IST)
        )

    finally:
        db.close()

# =========================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_candles()

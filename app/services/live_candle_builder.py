import json
import redis
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from sqlalchemy import text
from app.db import SessionLocal

log = logging.getLogger("live_candle_builder")

IST = ZoneInfo("Asia/Kolkata")
INTERVAL = 60  # 1 minute

# ===============================
# REDIS
# ===============================
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# ===============================
# MARKET TIME
# ===============================
def market_open(ts: datetime) -> bool:
    # Monday–Friday only
    if ts.weekday() >= 5:
        return False
    t = ts.time()
    return time(9, 15) <= t <= time(15, 30)

# ===============================
# FLOOR TIME
# ===============================
def floor_time(ts: datetime) -> int:
    epoch = int(ts.timestamp())
    return epoch - (epoch % INTERVAL)

# ===============================
# GET LAST DB CANDLE
# ===============================
def get_last_candle_from_db(token: int):
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT
                    extract(epoch from candle_time)::int AS time,
                    open, high, low, close, volume
                FROM zerodha_candles_1m
                WHERE instrument_token = :t
                ORDER BY candle_time DESC
                LIMIT 1
            """),
            {"t": token},
        ).first()

        if row:
            return dict(row._mapping)
        return None
    finally:
        db.close()

# ===============================
# SAVE CLOSED CANDLE
# ===============================
def save_closed_candle(token: int, candle: dict):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO zerodha_candles_1m
                (instrument_token, candle_time, open, high, low, close, volume)
                VALUES
                (:token, to_timestamp(:t), :o, :h, :l, :c, :v)
                ON CONFLICT DO NOTHING
            """),
            {
                "token": token,
                "t": candle["time"],
                "o": candle["open"],
                "h": candle["high"],
                "l": candle["low"],
                "c": candle["close"],
                "v": candle["volume"],
            },
        )
        db.commit()
        log.info("🕯️ Candle closed | token=%s time=%s", token, candle["time"])
    finally:
        db.close()

# ===============================
# MAIN TICK HANDLER
# ===============================
def process_tick(token: int, price: float, volume: int, exch_ts: datetime):
    """
    Returns LIVE candle dict for UI (running candle)
    """
    if not exch_ts:
        return None

    ts = exch_ts.astimezone(IST)

    if not market_open(ts):
        return None

    candle_start = floor_time(ts)
    key = f"live:candle:{token}:1m"

    raw = r.get(key)

    # =====================================================
    # FIRST TICK AFTER UI / SERVER START
    # =====================================================
    if not raw:
        last_db = get_last_candle_from_db(token)

        # 🔥 SAME RUNNING CANDLE (MERGE)
        if last_db and last_db["time"] == candle_start:
            candle = {
                "time": candle_start,
                "open": last_db["open"],
                "high": max(last_db["high"], price),
                "low": min(last_db["low"], price),
                "close": price,
                "volume": last_db["volume"],
                "last_tick_volume": volume,
            }
        else:
            # 🔥 BRAND NEW CANDLE
            candle = {
                "time": candle_start,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0,
                "last_tick_volume": volume,
            }

        r.set(key, json.dumps(candle))
        return candle

    candle = json.loads(raw)

    # =====================================================
    # SAME MINUTE → UPDATE RUNNING CANDLE
    # =====================================================
    if candle["time"] == candle_start:
        tick_vol = max(volume - candle.get("last_tick_volume", volume), 0)

        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["close"] = price
        candle["volume"] += tick_vol
        candle["last_tick_volume"] = volume

        r.set(key, json.dumps(candle))
        return candle

    # =====================================================
    # NEW MINUTE → CLOSE OLD, START NEW
    # =====================================================
    save_closed_candle(token, candle)

    new_candle = {
        "time": candle_start,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": 0,
        "last_tick_volume": volume,
    }

    r.set(key, json.dumps(new_candle))
    return new_candle

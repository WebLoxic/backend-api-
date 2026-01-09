# app/services/candle_aggregator.py

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import text
from app.db import SessionLocal

IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# TIMEFRAME DEFINITIONS (seconds)
# =====================================================
TIMEFRAME_SECONDS = {
    # "5s": 5,
    # "10s": 10,
    # "15s": 15,
    # "20s": 20,
    # "30s": 30,
    "2m": 2,
    "3m": 3,
    "4m": 4,
    "5m": 5,
    "10m": 10,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "1d": 1440,
    "1w": 10080,
    "1M": 43200,  # approx (30 days)

}

# =====================================================
# HELPERS
# =====================================================
def floor_time(ts: int, interval: int) -> int:
    return ts - (ts % interval)


def floor_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# =====================================================
# CORE AGGREGATION LOGIC
# =====================================================
def aggregate_from_1m(
    instrument_token: int,
    timeframe: str,
    lookback: int = 500
):
    """
    Aggregates candles from zerodha_candles_1m
    and returns aggregated OHLCV
    """

    db = SessionLocal()

    try:
        rows = db.execute(
            text("""
                SELECT
                    EXTRACT(EPOCH FROM candle_time)::int AS ts,
                    open, high, low, close, volume
                FROM zerodha_candles_1m
                WHERE instrument_token = :token
                ORDER BY candle_time DESC
                LIMIT :limit
            """),
            {
                "token": instrument_token,
                "limit": lookback
            }
        ).fetchall()

        if not rows:
            return []

        rows = list(reversed(rows))  # oldest → newest
        buckets = {}

        for r in rows:
            ts = int(r.ts)

            # -----------------------------
            # MONTHLY
            # -----------------------------
            if timeframe == "1M":
                dt = datetime.fromtimestamp(ts, IST)
                bucket_dt = floor_month(dt)
                bucket_key = int(bucket_dt.timestamp())

            # -----------------------------
            # NORMAL TIMEFRAMES
            # -----------------------------
            else:
                interval = TIMEFRAME_SECONDS[timeframe]
                bucket_key = floor_time(ts, interval)

            if bucket_key not in buckets:
                buckets[bucket_key] = {
                    "time": bucket_key,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
            else:
                b = buckets[bucket_key]
                b["high"] = max(b["high"], r.high)
                b["low"] = min(b["low"], r.low)
                b["close"] = r.close
                b["volume"] += r.volume

        return list(buckets.values())

    finally:
        db.close()

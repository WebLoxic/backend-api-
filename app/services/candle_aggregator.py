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
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "20s": 20,
    "30s": 30,

    "1m": 60,
    "2m": 120,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,

    "1h": 3600,
    "4h": 14400,

    "1d": 86400,
    "7d": 604800,

    # Monthly handled separately
    "1M": "MONTH"
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

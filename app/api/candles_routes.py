

# from fastapi import APIRouter, Query, HTTPException
# from datetime import datetime, timedelta
# from app.kite_client import kite_client

# router = APIRouter(prefix="/candles", tags=["Candles"])


# @router.get("/historical")
# def historical_candles(
#     token: int = Query(...),
#     interval: str = Query("minute"),
#     days: int = Query(1),
# ):
#     """
#     Zerodha historical candles + current market snapshot

#     interval: minute / 3minute / 5minute / 15minute / day
#     days: lookback days
#     """

#     kite = kite_client.get_user_kite(user_id=1)

#     to_date = datetime.now()
#     from_date = to_date - timedelta(days=days)

#     # ===============================
#     # 1️⃣ FETCH HISTORICAL CANDLES
#     # ===============================
#     try:
#         candles = kite.historical_data(
#             instrument_token=token,
#             from_date=from_date,
#             to_date=to_date,
#             interval=interval,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Historical fetch failed: {e}")

#     formatted_candles = [
#         {
#             "time": int(c["date"].timestamp()),
#             "open": c["open"],
#             "high": c["high"],
#             "low": c["low"],
#             "close": c["close"],
#             "volume": c["volume"],
#         }
#         for c in candles
#     ]

#     # ===============================
#     # 2️⃣ FETCH CURRENT MARKET SNAPSHOT
#     # ===============================
#     snapshot = None
#     try:
#         # Zerodha quote API (current truth, NOT live tick)
#         quote = kite.quote([token])
#         q = list(quote.values())[0]

#         last_trade_time = q.get("last_trade_time") or q.get("exchange_timestamp")

#         snapshot = {
#             "ltp": q.get("last_price"),
#             "last_trade_time": int(last_trade_time.timestamp())
#             if last_trade_time
#             else None,
#             "ohlc": q.get("ohlc"),
#         }

#     except Exception:
#         # Snapshot failure should NOT break historical candles
#         snapshot = None

#     # ===============================
#     # 3️⃣ FINAL RESPONSE
#     # ===============================
#     return {
#         "candles": formatted_candles,
#         "snapshot": snapshot,
#     }






from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta

from app.kite_client import kite_client
from app.services.candle_aggregator import aggregate_from_1m

router = APIRouter(prefix="/candles", tags=["Candles"])

# ============================================================
# 1️⃣ HISTORICAL CANDLES + CURRENT SNAPSHOT (UNCHANGED LOGIC)
# ============================================================
@router.get("/historical")
def historical_candles(
    token: int = Query(...),
    interval: str = Query("minute"),
    days: int = Query(1),
):
    """
    Zerodha historical candles + current market snapshot

    interval: minute / 3minute / 5minute / 15minute / day
    days: lookback days
    """

    kite = kite_client.get_user_kite(user_id=1)

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)

    # ===============================
    # 1️⃣ FETCH HISTORICAL CANDLES
    # ===============================
    try:
        candles = kite.historical_data(
            instrument_token=token,
            from_date=from_date,
            to_date=to_date,
            interval=interval,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Historical fetch failed: {e}"
        )

    formatted_candles = [
        {
            "time": int(c["date"].timestamp()),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"],
        }
        for c in candles
    ]

    # ===============================
    # 2️⃣ FETCH CURRENT SNAPSHOT (QUOTE)
    # ===============================
    snapshot = None
    try:
        quote = kite.quote([token])
        q = list(quote.values())[0]

        last_trade_time = (
            q.get("last_trade_time")
            or q.get("exchange_timestamp")
        )

        snapshot = {
            "ltp": q.get("last_price"),
            "last_trade_time": (
                int(last_trade_time.timestamp())
                if last_trade_time else None
            ),
            "ohlc": q.get("ohlc"),
        }

    except Exception:
        # Snapshot failure must NOT break chart
        snapshot = None

    return {
        "candles": formatted_candles,
        "snapshot": snapshot,
    }

# ============================================================
# 2️⃣ AGGREGATED CANDLES (ZERODHA-STYLE MULTI-TF)
# ============================================================
@router.get("/aggregated")
def aggregated_candles(
    token: int = Query(...),
    tf: str = Query("5m"),
    limit: int = Query(500),
):
    """
    Multi-timeframe candles aggregated from 1-minute base candles

    Supported TF:
    5s,10s,15s,20s,30s,
    1m,2m,5m,10m,15m,30m,
    1h,4h,
    1d,7d,1M
    """

    try:
        data = aggregate_from_1m(
            instrument_token=token,
            timeframe=tf,
            lookback=limit
        )
        return data

    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe: {tf}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Aggregation failed: {e}"
        )

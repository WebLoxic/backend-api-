import asyncio
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import redis

from app.services.candle_aggregator import TIMEFRAME_SECONDS

log = logging.getLogger("mtf_ws")

router = APIRouter()

IST = ZoneInfo("Asia/Kolkata")

# Redis (same Redis which candle_builder uses)
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# =====================================================
# HELPERS
# =====================================================
def floor_time(ts: int, interval: int) -> int:
    return ts - (ts % interval)


def floor_month(dt: datetime) -> int:
    return int(
        dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )


# =====================================================
# WEBSOCKET: LIVE MTF
# =====================================================
@router.websocket("/ws/mtf/{token}")
async def mtf_websocket(
    websocket: WebSocket,
    token: int,
    tf: str = Query("5m"),
):
    """
    LIVE multi-timeframe WebSocket

    Example:
    ws://localhost:8000/ws/mtf/2953217?tf=5m
    """

    await websocket.accept()
    log.info(f"🟢 MTF WS connected | token={token} | tf={tf}")

    if tf not in TIMEFRAME_SECONDS:
        await websocket.send_json({
            "type": "error",
            "message": f"Unsupported timeframe: {tf}"
        })
        await websocket.close()
        return

    interval = TIMEFRAME_SECONDS[tf]

    pubsub = redis_client.pubsub()
    pubsub.psubscribe(f"candle:{token}")

    forming = None

    try:
        async for msg in pubsub.listen():
            if msg["type"] != "pmessage":
                continue

            raw = json.loads(msg["data"])

            """
            raw candle format from candle_builder:
            {
              time, open, high, low, close, volume
            }
            """

            ts = raw["time"]

            # ------------------------------
            # MONTHLY
            # ------------------------------
            if tf == "1M":
                bucket = floor_month(
                    datetime.fromtimestamp(ts, IST)
                )
            else:
                bucket = floor_time(ts, interval)

            # ------------------------------
            # NEW FORMING CANDLE
            # ------------------------------
            if not forming or forming["time"] != bucket:
                forming = {
                    "time": bucket,
                    "open": raw["open"],
                    "high": raw["high"],
                    "low": raw["low"],
                    "close": raw["close"],
                    "volume": raw["volume"],
                }
            else:
                forming["high"] = max(forming["high"], raw["high"])
                forming["low"] = min(forming["low"], raw["low"])
                forming["close"] = raw["close"]
                forming["volume"] += raw["volume"]

            # ------------------------------
            # PUSH LIVE FORMING CANDLE
            # ------------------------------
            await websocket.send_json({
                "type": "candle",
                "data": forming
            })

    except WebSocketDisconnect:
        log.info(f"🔴 MTF WS disconnected | token={token} | tf={tf}")

    except Exception as e:
        log.exception(f"❌ MTF WS error: {e}")

    finally:
        pubsub.close()

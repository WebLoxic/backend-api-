# from fastapi import WebSocket, APIRouter
# import redis, json, asyncio

# router = APIRouter()
# r = redis.Redis(decode_responses=True)

# @router.websocket("/ws/market")
# async def market_ws(ws: WebSocket):
#     await ws.accept()
#     while True:
#         tick = r.get("tick:256265")
#         if tick:
#             await ws.send_json(json.loads(tick))
#         await asyncio.sleep(1)




from fastapi import WebSocket, APIRouter, Query
import redis, json, asyncio
from zoneinfo import ZoneInfo
from datetime import datetime, time as dtime

router = APIRouter()
r = redis.Redis(decode_responses=True)

IST = ZoneInfo("Asia/Kolkata")

def market_is_open():
    now = datetime.now(IST).time()
    return dtime(9, 15) <= now <= dtime(15, 30)

@router.websocket("/ws/market")
async def market_ws(
    ws: WebSocket,
    token: int = Query(...)
):
    await ws.accept()
    redis_key = f"tick:{token}"

    try:
        while True:
            tick_raw = r.get(redis_key)
            if tick_raw and market_is_open():
                tick = json.loads(tick_raw)

                # ✅ STRICT VALIDATION
                if (
                    "ltp" in tick and
                    "instrument_token" in tick and
                    tick["instrument_token"] == token and
                    "exchange_timestamp" in tick
                ):
                    await ws.send_json({
                        "instrument_token": token,
                        "ltp": tick["ltp"],
                        "volume": tick.get("volume"),
                        "timestamp": tick["exchange_timestamp"]
                    })

            await asyncio.sleep(0.25)  # Zerodha-like latency
    except:
        await ws.close()

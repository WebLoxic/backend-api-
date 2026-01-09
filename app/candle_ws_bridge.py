# app/candle_ws_bridge.py

import asyncio
import json
import redis
import logging
from app.ws_manager import ws_manager

log = logging.getLogger("candle_ws_bridge")

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def candle_ws_bridge():
    pubsub = r.pubsub()
    pubsub.psubscribe("candle:*")

    log.info("🔥 Candle WS Bridge STARTED (Redis → UI)")

    while True:
        try:
            msg = pubsub.get_message(ignore_subscribe_messages=True)
            if not msg:
                await asyncio.sleep(0.05)
                continue

            channel = msg["channel"]   # candle:633601
            token = int(channel.split(":")[1])
            candle = json.loads(msg["data"])

            log.info(f"📤 PUSH CANDLE → UI | token={token} | {candle}")

            await ws_manager.broadcast_to_token(
                token,
                {
                    "type": "candle",
                    "data": candle
                }
            )

        except Exception as e:
            log.exception(f"❌ Candle WS bridge error: {e}")
            await asyncio.sleep(1)


# 🔥 THIS WAS MISSING
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(candle_ws_bridge())

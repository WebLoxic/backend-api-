# app/ws/market_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from kiteconnect import KiteTicker
import json
import logging
from typing import Dict, List, Set

from app.kite_client import kite_client
from app.core.time_utils import ist_now

router = APIRouter()
log = logging.getLogger("market_ws")

# =====================================================
# Frontend websocket clients
# token -> list[WebSocket]
# =====================================================
active_clients: Dict[int, List[WebSocket]] = {}

# =====================================================
# Zerodha WS (single global connection)
# =====================================================
kws: KiteTicker | None = None
subscribed_tokens: Set[int] = set()
queued_tokens: Set[int] = set()

# =====================================================
# Zerodha tick callback
# =====================================================
def on_ticks(ws, ticks):
    if not ticks:
        log.warning("⚠️ on_ticks called with empty ticks")
        return

    for t in ticks:
        log.info("🔥 RAW TICK RECEIVED: %s", t)

        token = t["instrument_token"]

        payload = {
            "instrument_token": token,
            "ltp": t.get("last_price"),
            "volume": t.get("volume_traded", 0),
            "exchange_timestamp": (
                t["exchange_timestamp"].isoformat()
                if t.get("exchange_timestamp")
                else None
            ),
        }

        if token in active_clients:
            for client in list(active_clients[token]):
                try:
                    client.send_text(json.dumps(payload))
                except Exception as e:
                    log.error("WS send error: %s", e)


def on_connect(ws, response):
    log.info("🟢 Zerodha WS connected")

    if queued_tokens:
        tokens = list(queued_tokens)
        kws.subscribe(tokens)
        kws.set_mode(kws.MODE_FULL, tokens)
        subscribed_tokens.update(tokens)
        queued_tokens.clear()

        log.info("📡 Subscribed queued tokens on connect: %s", tokens)
    else:
        log.warning("📦 QUEUED TOKENS AT CONNECT: []")


def on_close(ws, code, reason):
    log.warning("❌ Zerodha WS closed | %s %s", code, reason)


def on_error(ws, code, reason):
    log.error("🔥 Zerodha WS error | %s %s", code, reason)


# =====================================================
# Start Zerodha WS (once)
# =====================================================
def ensure_zerodha_ws():
    global kws

    if kws:
        return

    kite = kite_client.get_user_kite(user_id=1)

    kws = KiteTicker(kite.api_key, kite.access_token)

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close
    kws.on_error = on_error

    kws.connect(threaded=True)
    log.info("🟢 Starting Zerodha Market WebSocket")


# =====================================================
# Frontend WebSocket endpoint
# =====================================================
@router.websocket("/ws/market")
async def market_ws(ws: WebSocket, token: int):
    """
    Frontend connects:
    ws://localhost:8000/ws/market?token=633601
    """

    await ws.accept()
    ensure_zerodha_ws()

    # register frontend client
    active_clients.setdefault(token, []).append(ws)
    log.info("🧩 Client connected | token=%s", token)

    # subscribe token (or queue it)
    if token not in subscribed_tokens:
        if kws and kws.is_connected():
            kws.subscribe([token])
            kws.set_mode(kws.MODE_FULL, [token])
            subscribed_tokens.add(token)
            log.info("📡 Subscribed token=%s MODE_FULL", token)
        else:
            queued_tokens.add(token)
            log.warning("⏳ Token queued until WS connects: %s", token)

    try:
        while True:
            await ws.receive_text()  # keep alive

    except WebSocketDisconnect:
        pass

    finally:
        # cleanup client
        active_clients[token].remove(ws)
        if not active_clients[token]:
            del active_clients[token]

        log.info("🔌 Client disconnected | token=%s", token)

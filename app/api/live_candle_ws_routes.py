from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws_manager import ws_manager
import logging

log = logging.getLogger("live_candle_ws")

router = APIRouter(tags=["ws-candles"])


@router.websocket("/ws/candles/{token}")
async def live_candle_ws(websocket: WebSocket, token: int):
    await websocket.accept()  # ✅ MUST BE FIRST

    # 🔒 SAFE REGISTER
    ws_manager.clients.setdefault(token, set()).add(websocket)

    log.info(f"🟢 Candle WS connected | token={token}")

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_manager.clients[token].discard(websocket)

        # cleanup empty set
        if not ws_manager.clients[token]:
            ws_manager.clients.pop(token, None)

        log.info(f"🔴 Candle WS disconnected | token={token}")

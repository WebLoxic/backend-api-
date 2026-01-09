from fastapi import APIRouter, WebSocket
from app.streamer import market_broadcaster, ui_streamer

router = APIRouter()

@router.websocket("/ws/market-raw/{token}")
async def ws_market_raw(ws: WebSocket, token: int):
    await market_broadcaster.connect(token, ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except:
        market_broadcaster.disconnect(token, ws)

@router.websocket("/ws/market-ui/{token}")
async def ws_market_ui(ws: WebSocket, token: int):
    await ui_streamer.connect(token, ws)
    try:
        while True:
            await ws.receive_text()
    except:
        ui_streamer.disconnect(token, ws)

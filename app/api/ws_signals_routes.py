from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.signal_broadcaster import broadcaster

router = APIRouter(
    prefix="/ws/signals",
    tags=["WS-Signals"]
)


@router.websocket("")
async def ws_signals(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            # keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)

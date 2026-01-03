# app/ws_frontend.py
from fastapi import WebSocket, WebSocketDisconnect
from app.subscription_manager import SubscriptionManager

subscription_manager: SubscriptionManager = None

async def ws_handler(websocket: WebSocket, user_id: int):
    await websocket.accept()

    try:
        while True:
            msg = await websocket.receive_json()

            action = msg.get("action")
            token = msg.get("instrument_token")

            if action == "subscribe":
                await subscription_manager.subscribe(user_id, token)

            elif action == "unsubscribe":
                await subscription_manager.unsubscribe(user_id, token)

    except WebSocketDisconnect:
        await subscription_manager.cleanup_user(user_id)

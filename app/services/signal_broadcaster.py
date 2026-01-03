# app/services/signal_broadcaster.py

from typing import Set
from fastapi import WebSocket
import asyncio
import logging

log = logging.getLogger("signal_broadcaster")


class SignalBroadcaster:
    """
    Central WS broadcaster for strategy / signal events
    """

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        log.info(f"📡 WS connected | total={len(self._connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.discard(websocket)
        log.info(f"❌ WS disconnected | total={len(self._connections)}")

    async def broadcast(self, payload: dict):
        """
        Send signal payload to all connected clients
        """
        async with self._lock:
            dead = []
            for ws in self._connections:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)

            for ws in dead:
                self._connections.discard(ws)

        if payload:
            log.debug(f"📢 Signal broadcasted to {len(self._connections)} clients")


# ✅ SINGLETON INSTANCE (IMPORTANT)
broadcaster = SignalBroadcaster()

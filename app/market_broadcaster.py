from fastapi import WebSocket
import logging

log = logging.getLogger("market_broadcaster")

class MarketBroadcaster:
    def __init__(self):
        # token -> set of websocket clients
        self.clients = {}

    async def connect(self, token: int, ws: WebSocket):
        self.clients.setdefault(token, set()).add(ws)
        log.info(f"🔌 WS client connected for token {token}")

    async def disconnect(self, token: int, ws: WebSocket):
        if token in self.clients:
            self.clients[token].discard(ws)
            if not self.clients[token]:
                del self.clients[token]
        log.info(f"❌ WS client disconnected for token {token}")

    async def broadcast_tick(self, tick: dict):
        token = tick["instrument_token"]
        if token not in self.clients:
            return

        dead = []
        for ws in self.clients[token]:
            try:
                await ws.send_json(tick)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.clients[token].discard(ws)

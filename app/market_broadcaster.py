# import logging
# from typing import Dict, Set
# from fastapi import WebSocket

# log = logging.getLogger("market_broadcaster")


# class MarketBroadcaster:
#     def __init__(self):
#         # token -> set(WebSocket)
#         self.clients: Dict[int, Set[WebSocket]] = {}

#     async def connect(self, token: int, ws: WebSocket):
#         self.clients.setdefault(token, set()).add(ws)
#         log.info(
#             f"🟢 UI WS connected | token={token} | total={len(self.clients[token])}"
#         )

#     async def disconnect(self, token: int, ws: WebSocket):
#         if token in self.clients:
#             self.clients[token].discard(ws)
#             if not self.clients[token]:
#                 del self.clients[token]

#         log.info(f"🔴 UI WS disconnected | token={token}")

#     async def broadcast_tick(self, payload: dict):
#         """
#         Called from MarketWebSocket (async-safe)
#         """
#         token = payload.get("instrument_token")
#         if not token:
#             return

#         sockets = self.clients.get(token)
#         if not sockets:
#             return

#         dead = []
#         for ws in sockets:
#             try:
#                 await ws.send_json(payload)
#             except Exception:
#                 dead.append(ws)

#         for ws in dead:
#             sockets.discard(ws)







import logging
from typing import Dict, Set
from fastapi import WebSocket

log = logging.getLogger("market_broadcaster")


class MarketBroadcaster:
    def __init__(self):
        # instrument_token -> set(WebSocket)
        self.clients: Dict[int, Set[WebSocket]] = {}

    async def connect(self, token: int, ws: WebSocket):
        self.clients.setdefault(token, set()).add(ws)
        log.info(
            f"🟢 UI WS connected | token={token} | total={len(self.clients[token])}"
        )

    async def disconnect(self, token: int, ws: WebSocket):
        if token in self.clients:
            self.clients[token].discard(ws)
            if not self.clients[token]:
                del self.clients[token]

        log.info(f"🔴 UI WS disconnected | token={token}")

    async def broadcast_tick(self, tick: dict):
        """
        Receives RAW Zerodha tick and broadcasts to UI
        """
        token = tick.get("instrument_token")
        if not token:
            return

        sockets = self.clients.get(token)
        if not sockets:
            return

        payload = {
            "type": "tick",   # 🔥 VERY IMPORTANT
            "data": tick      # 🔥 FULL RAW ZERODHA TICK
        }

        dead = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            sockets.discard(ws)




# import json, logging
# from typing import List
# from fastapi import WebSocket

# logger = logging.getLogger(__name__)

# class ConnectionManager:
#     def __init__(self):
#         self.connections: List[WebSocket] = []

#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.connections.append(websocket)
#         logger.info("WS client connected. total=%d", len(self.connections))

#     async def disconnect(self, websocket: WebSocket):
#         try: self.connections.remove(websocket)
#         except ValueError: pass
#         logger.info("WS client disconnected. total=%d", len(self.connections))

#     async def broadcast_json(self, message: dict):
#         for conn in list(self.connections):
#             try:
#                 await conn.send_json(message)
#                 print("📡 SENT:", message)
#             except:
#                 await self.disconnect(conn)

# manager = ConnectionManager()


# async def publish_signal(data: dict):
#     """Send ML prediction to all WebSocket clients"""
#     print("📡 PUBLISH:", data)
#     await manager.broadcast_json(data)







# app/ws_manager.py

from collections import defaultdict
from fastapi import WebSocket

class WSManager:
    def __init__(self):
        self.clients = defaultdict(set)

    async def broadcast_to_token(self, token: int, data: dict):
        if token not in self.clients:
            return

        dead = set()
        for ws in self.clients[token]:
            try:
                await ws.send_json(data)
            except:
                dead.add(ws)

        for ws in dead:
            self.clients[token].discard(ws)

ws_manager = WSManager()

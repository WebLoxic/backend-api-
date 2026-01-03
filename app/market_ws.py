# import asyncio
# import logging
# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")


# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster):
#         """
#         broadcaster must have:
#             async def broadcast_tick(payload: dict)
#         """
#         self.broadcaster = broadcaster
#         self.subscribed_tokens = set()
#         self.last_state = {}

#         self.ticker = KiteTicker(api_key, access_token)

#         # ===============================
#         # ZERODHA CALLBACKS (ALL REQUIRED)
#         # ===============================
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     # =====================================================
#     # WS LIFECYCLE
#     # =====================================================
#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     def on_connect(self, ws, response):
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)
#             log.info(f"🔁 Re-subscribed {len(tokens)} tokens")

#     def on_close(self, ws, code, reason):
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     # =====================================================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # =====================================================
#     def subscribe(self, token: int):
#         token = int(token)

#         if token in self.subscribed_tokens:
#             return

#         # 🔥 REST SNAPSHOT SEED (IMPORTANT)
#         try:
#             quote = self.ticker.kite.quote([f"NSE:{token}"])
#             data = list(quote.values())[0]

#             self.last_state[token] = {
#                 "instrument_token": token,
#                 "ltp": data.get("last_price"),
#                 "volume": data.get("volume"),
#                 "ohlc": data.get("ohlc"),
#                 "change": (
#                     data["last_price"] - data["ohlc"]["close"]
#                     if data.get("ohlc")
#                     else None
#                 ),
#                 "timestamp": None,
#             }

#             log.info(f"📸 Seeded REST snapshot for {token}")

#         except Exception as e:
#             log.warning(f"⚠️ Snapshot fetch failed for {token}: {e}")

#         self.subscribed_tokens.add(token)
#         self.ticker.subscribe([token])
#         self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#         log.info(f"📡 Subscribed token {token} (FULL MODE)")

#     def unsubscribe(self, token: int):
#         token = int(token)

#         if token not in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.remove(token)
#         self.ticker.unsubscribe([token])

#         log.info(f"🛑 Unsubscribed token {token}")

#     # =====================================================
#     # 🔥 TICKS HANDLER (THIS WAS MISSING)
#     # =====================================================
#     def on_ticks(self, ws, ticks):
#         try:
#             loop = asyncio.get_running_loop()
#         except RuntimeError:
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)

#         for tick in ticks:
#             token = tick.get("instrument_token")

#             prev = self.last_state.get(token, {})
#             ohlc = tick.get("ohlc") or prev.get("ohlc") or {}

#             ltp = tick.get("last_price") or prev.get("ltp")
#             close = ohlc.get("close")

#             payload = {
#                 "instrument_token": token,
#                 "ltp": ltp,
#                 "volume": tick.get("volume_traded") or prev.get("volume"),
#                 "ohlc": {
#                     "open": ohlc.get("open"),
#                     "high": ohlc.get("high"),
#                     "low": ohlc.get("low"),
#                     "close": close,
#                 },
#                 "change": (ltp - close) if ltp and close else None,
#                 "timestamp": (
#                     tick.get("exchange_timestamp").isoformat()
#                     if tick.get("exchange_timestamp")
#                     else None
#                 ),
#             }

#             self.last_state[token] = payload

#             loop.call_soon_threadsafe(
#                 asyncio.create_task,
#                 self.broadcaster.broadcast_tick(payload)
#             )


import asyncio
import logging
from kiteconnect import KiteTicker

log = logging.getLogger("market_ws")


class MarketWebSocket:
    """
    Zerodha KiteTicker → FastAPI Broadcaster
    Fully race-condition safe
    """

    def __init__(self, api_key: str, access_token: str, broadcaster):
        """
        broadcaster must expose:
            async def broadcast_tick(payload: dict)
        """
        self.broadcaster = broadcaster

        self.subscribed_tokens = set()
        self.last_state = {}

        # 🔐 WS STATE FLAGS
        self.ws_ready = False

        # ✅ SINGLE EVENT LOOP
        self.loop = asyncio.get_event_loop()

        self.ticker = KiteTicker(api_key, access_token)

        # ===============================
        # ZERODHA CALLBACKS
        # ===============================
        self.ticker.on_connect = self.on_connect
        self.ticker.on_ticks = self.on_ticks
        self.ticker.on_close = self.on_close
        self.ticker.on_error = self.on_error
        self.ticker.on_reconnect = self.on_reconnect
        self.ticker.on_noreconnect = self.on_noreconnect

    # =====================================================
    # WS LIFECYCLE
    # =====================================================
    def start(self):
        log.info("🟢 Starting Zerodha Market WebSocket")
        self.ticker.connect(threaded=True)

    def on_connect(self, ws, response):
        self.ws_ready = True
        log.info("🟢 Zerodha WS connected")

        tokens = list(self.subscribed_tokens)
        log.warning(f"📦 QUEUED TOKENS AT CONNECT: {tokens}")

        if not tokens:
            return

        self.ticker.subscribe(tokens)
        self.ticker.set_mode(self.ticker.MODE_LTP, tokens)

        log.error(f"📡 SUBSCRIBED AFTER CONNECT: {tokens}")

    def on_close(self, ws, code, reason):
        self.ws_ready = False
        log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

    def on_error(self, ws, code, reason):
        log.error(f"❌ Zerodha WS error: {code} | {reason}")

    def on_reconnect(self, attempts_count):
        log.warning(f"🔄 Zerodha WS reconnecting (attempt {attempts_count})")

    def on_noreconnect(self):
        log.critical("❌ Zerodha WS stopped reconnecting")

    # =====================================================
    # SUBSCRIBE / UNSUBSCRIBE
    # =====================================================
    def subscribe(self, token: int):
        token = int(token)

        if token in self.subscribed_tokens:
            return

        self.subscribed_tokens.add(token)
        log.error(f"🧲 TOKEN QUEUED FROM FRONTEND: {token}")

        # 🔥 If WS already connected → subscribe immediately
        if self.ws_ready:
            self.ticker.subscribe([token])
            self.ticker.set_mode(self.ticker.MODE_LTP, [token])
            log.error(f"📡 SUBSCRIBED IMMEDIATELY: {token}")

    def unsubscribe(self, token: int):
        token = int(token)

        if token not in self.subscribed_tokens:
            return

        self.subscribed_tokens.remove(token)
        self.last_state.pop(token, None)

        if self.ws_ready:
            self.ticker.unsubscribe([token])

        log.warning(f"🛑 UNSUBSCRIBED TOKEN: {token}")

    # =====================================================
    # 🔥 LIVE TICKS HANDLER
    # =====================================================
    def on_ticks(self, ws, ticks):
        """
        Called from Zerodha thread.
        Safely forwarded to asyncio loop.
        """

        if not ticks:
            return

        log.error(f"🔥 LIVE TICKS RECEIVED: {ticks}")

        for tick in ticks:
            token = tick.get("instrument_token")
            if not token:
                continue

            prev = self.last_state.get(token, {})

            ltp = tick.get("last_price") or prev.get("ltp")
            ohlc = tick.get("ohlc") or prev.get("ohlc") or {}
            close = ohlc.get("close")

            payload = {
                "instrument_token": token,
                "ltp": ltp,
                "volume": tick.get("volume_traded", prev.get("volume")),
                "ohlc": {
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "close": close,
                },
                "change": (ltp - close) if ltp and close else None,
                "timestamp": (
                    tick["exchange_timestamp"].isoformat()
                    if tick.get("exchange_timestamp")
                    else None
                ),
            }

            self.last_state[token] = payload

            # ✅ SAFE PUSH TO FASTAPI WS
            self.loop.call_soon_threadsafe(
                asyncio.create_task,
                self.broadcaster.broadcast_tick(payload)
            )

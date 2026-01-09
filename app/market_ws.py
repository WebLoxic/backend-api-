# # app/market_ws.py

# import asyncio
# import logging
# from typing import Set

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")


# class MarketWebSocket:
#     """
#     Zerodha KiteTicker → FastAPI WebSocket Broadcaster
#     Thread-safe, single source of truth
#     """

#     def __init__(self, api_key: str, access_token: str, broadcaster):
#         """
#         broadcaster MUST expose:
#             async def broadcast(token: int, payload: dict)
#         """

#         self.broadcaster = broadcaster

#         self.subscribed_tokens: Set[int] = set()
#         self.ws_ready = False

#         # IMPORTANT: capture FastAPI event loop
#         try:
#             self.loop = asyncio.get_running_loop()
#         except RuntimeError:
#             self.loop = asyncio.get_event_loop()

#         self.ticker = KiteTicker(api_key, access_token)

#         # Zerodha callbacks
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error
#         self.ticker.on_reconnect = self.on_reconnect
#         self.ticker.on_noreconnect = self.on_noreconnect

#     # =====================================================
#     # START
#     # =====================================================
#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # =====================================================
#     # ZERODHA EVENTS
#     # =====================================================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_LTP, tokens)
#             log.warning(f"📡 RESUBSCRIBED TOKENS: {tokens}")

#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     def on_reconnect(self, attempts):
#         log.warning(f"🔄 Zerodha WS reconnecting (attempt {attempts})")

#     def on_noreconnect(self):
#         log.critical("❌ Zerodha WS stopped reconnecting")

#     # =====================================================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # =====================================================
#     def subscribe(self, token: int):
#         token = int(token)

#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 TOKEN SUBSCRIBE REQUEST: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_LTP, [token])
#             log.info(f"📡 SUBSCRIBED IMMEDIATELY: {token}")

#     def unsubscribe(self, token: int):
#         token = int(token)

#         if token not in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.remove(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#         log.info(f"🛑 UNSUBSCRIBED TOKEN: {token}")

#     # =====================================================
#     # 🔥 LIVE TICKS
#     # =====================================================
#     def on_ticks(self, ws, ticks):
#         """
#         Zerodha thread → FastAPI asyncio loop
#         """

#         if not ticks:
#             return

#         for tick in ticks:
#             token = tick.get("instrument_token")
#             ltp = tick.get("last_price")

#             if not token or ltp is None:
#                 continue

#             payload = {
#                 "type": "TICK",
#                 "token": token,
#                 "ltp": ltp,
#                 "timestamp": (
#                     tick["exchange_timestamp"].isoformat()
#                     if tick.get("exchange_timestamp")
#                     else None
#                 ),
#             }

#             # SAFE cross-thread dispatch
#             self.loop.call_soon_threadsafe(
#                 asyncio.create_task,
#                 self.broadcaster.broadcast(token, payload)
#             )


# import asyncio
# import logging
# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")


# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster):
#         self.broadcaster = broadcaster
#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         # 🔥 correct loop
#         self.loop = asyncio.get_running_loop()

#         self.ticker = KiteTicker(api_key, access_token)

#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)
#             log.info(f"📡 SUBSCRIBED AFTER CONNECT: {tokens}")

#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     def subscribe(self, token: int):
#         token = int(token)

#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 TOKEN SUBSCRIBE REQUEST: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])
#             log.info(f"📡 SUBSCRIBED IMMEDIATELY: {token}")

#     def unsubscribe(self, token: int):
#         token = int(token)

#         if token not in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.remove(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#         log.info(f"🛑 UNSUBSCRIBED TOKEN: {token}")

#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         log.info(f"🔥 LIVE TICKS RECEIVED: {ticks}")

#         for tick in ticks:
#             payload = {
#                 "instrument_token": tick["instrument_token"],
#                 "ltp": tick.get("last_price"),
#                 "ohlc": tick.get("ohlc"),
#                 "volume": tick.get("volume_traded"),
#                 "timestamp": tick.get("exchange_timestamp").isoformat()
#                 if tick.get("exchange_timestamp")
#                 else None,
#             }

#             asyncio.run_coroutine_threadsafe(
#                 self.broadcaster.broadcast_tick(payload),
#                 self.loop,
#             )





# # app/market_ws.py

# import asyncio
# import logging
# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")


# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster, loop):
#         self.broadcaster = broadcaster
#         self.loop = loop               # ✅ FastAPI event loop
#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         self.ticker = KiteTicker(api_key, access_token)

#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)
#             log.info(f"📡 SUBSCRIBED AFTER CONNECT: {tokens}")

#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 TOKEN SUBSCRIBE REQUEST: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])
#             log.info(f"📡 SUBSCRIBED IMMEDIATELY: {token}")

#     def unsubscribe(self, token: int):
#         token = int(token)
#         if token not in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.remove(token)
#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#         log.info(f"🛑 UNSUBSCRIBED TOKEN: {token}")

#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         log.info(f"🔥 LIVE RAW TICKS RECEIVED: {ticks}")

#         for raw_tick in ticks:
#             # 🔥 CORRECT WAY: send coroutine to FastAPI loop
#             asyncio.run_coroutine_threadsafe(
#                 self.broadcaster.broadcast_tick(raw_tick),
#                 self.loop,
#             )




# import asyncio
# import logging
# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster, loop):
#         self.broadcaster = broadcaster
#         self.loop = loop
#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)
#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         log.info(f"🔥 LIVE RAW TICKS RECEIVED: {ticks}")

#         for raw_tick in ticks:
#             asyncio.run_coroutine_threadsafe(
#                 self.broadcaster.broadcast_tick(raw_tick),
#                 self.loop
#             )






# import asyncio
# import logging
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# IST = ZoneInfo("Asia/Kolkata")


# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster, loop):
#         self.broadcaster = broadcaster
#         self.loop = loop
#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     # =========================
#     # START WS
#     # =========================
#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # =========================
#     # CONNECT
#     # =========================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     # =========================
#     # CLOSE / ERROR
#     # =========================
#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     # =========================
#     # SUBSCRIBE
#     # =========================
#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)
#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     # =========================
#     # DATETIME SERIALIZER
#     # =========================
#     def _serialize_value(self, v):
#         if isinstance(v, datetime):
#             return v.astimezone(IST).isoformat()
#         return v

#     def serialize_tick(self, tick: dict) -> dict:
#         """
#         Convert Zerodha raw tick to JSON safe tick
#         """
#         safe = {}

#         for k, v in tick.items():
#             if isinstance(v, dict):
#                 safe[k] = {kk: self._serialize_value(vv) for kk, vv in v.items()}
#             else:
#                 safe[k] = self._serialize_value(v)

#         return safe

#     # =========================
#     # ON TICKS (CORE)
#     # =========================
#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         log.info(f"🔥 LIVE RAW TICKS RECEIVED: {ticks}")

#         for raw_tick in ticks:
#             safe_tick = self.serialize_tick(raw_tick)

#             asyncio.run_coroutine_threadsafe(
#                 self.broadcaster.broadcast_tick(safe_tick),
#                 self.loop
#             )






# # app/market_ws.py

# import asyncio
# import logging
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# IST = ZoneInfo("Asia/Kolkata")
# UTC = ZoneInfo("UTC")


# class MarketWebSocket:
#     def __init__(self, api_key: str, access_token: str, broadcaster, loop):
#         self.broadcaster = broadcaster
#         self.loop = loop

#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     # =========================
#     # START WS
#     # =========================
#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # =========================
#     # CONNECT
#     # =========================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     # =========================
#     # CLOSE / ERROR
#     # =========================
#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     # =========================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # =========================
#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     # =========================
#     # SERIALIZATION
#     # =========================
#     def _serialize_value(self, v):
#         if isinstance(v, datetime):
#             return v.astimezone(IST).isoformat()
#         return v

#     def serialize_tick(self, tick: dict) -> dict:
#         safe = {}
#         for k, v in tick.items():
#             if isinstance(v, dict):
#                 safe[k] = {kk: self._serialize_value(vv) for kk, vv in v.items()}
#             else:
#                 safe[k] = self._serialize_value(v)
#         return safe

#     # =========================
#     # CORE: ON TICKS
#     # =========================
#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         for raw_tick in ticks:
#             try:
#                 safe_tick = self.serialize_tick(raw_tick)

#                 # ---------------------------------
#                 # 1️⃣ UI → FULL JSON (NO DATA LOSS)
#                 # ---------------------------------
#                 asyncio.run_coroutine_threadsafe(
#                     self.broadcaster.broadcast_tick(safe_tick),
#                     self.loop
#                 )

#                 # ---------------------------------
#                 # 2️⃣ REDIS → CANDLE INPUT (MINIMAL)
#                 # ---------------------------------
#                 exch_ts = safe_tick.get("exchange_timestamp")
#                 if not exch_ts:
#                     continue

#                 epoch_ts = int(
#                     datetime.fromisoformat(exch_ts)
#                     .astimezone(UTC)
#                     .timestamp()
#                 )

#                 token = safe_tick.get("instrument_token")
#                 price = safe_tick.get("last_price")

#                 if token is None or price is None:
#                     continue

#                 self.broadcaster.redis.xadd(
#                     f"tick_stream:{token}",
#                     {
#                         "ts": epoch_ts,
#                         "price": price,
#                         "volume": safe_tick.get("volume_traded", 0)
#                     }
#                 )

#             except Exception as e:
#                 log.exception(f"❌ on_ticks processing error: {e}")







# # app/market_ws.py

# import asyncio
# import logging
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# IST = ZoneInfo("Asia/Kolkata")
# UTC = ZoneInfo("UTC")


# class MarketWebSocket:
#     def __init__(
#         self,
#         api_key: str,
#         access_token: str,
#         broadcaster,
#         redis_client,      # ✅ REDIS INJECTED HERE
#         loop
#     ):
#         self.broadcaster = broadcaster
#         self.redis = redis_client    # ✅ STORE REDIS HERE
#         self.loop = loop

#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#     # =========================
#     # START WS
#     # =========================
#     def start(self):
#         log.info("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # =========================
#     # CONNECT
#     # =========================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         log.info("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     # =========================
#     # CLOSE / ERROR
#     # =========================
#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         log.error(f"❌ Zerodha WS error: {code} | {reason}")

#     # =========================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # =========================
#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         log.info(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     # =========================
#     # SERIALIZATION
#     # =========================
#     def _serialize_value(self, v):
#         if isinstance(v, datetime):
#             return v.astimezone(IST).isoformat()
#         return v

#     def serialize_tick(self, tick: dict) -> dict:
#         safe = {}
#         for k, v in tick.items():
#             if isinstance(v, dict):
#                 safe[k] = {kk: self._serialize_value(vv) for kk, vv in v.items()}
#             else:
#                 safe[k] = self._serialize_value(v)
#         return safe

#     # =========================
#     # CORE: ON TICKS
#     # =========================
#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         for raw_tick in ticks:
#             try:
#                 safe_tick = self.serialize_tick(raw_tick)

#                 # ---------------------------------
#                 # 1️⃣ UI → FULL JSON
#                 # ---------------------------------
#                 asyncio.run_coroutine_threadsafe(
#                     self.broadcaster.broadcast_tick(safe_tick),
#                     self.loop
#                 )

#                 # ---------------------------------
#                 # 2️⃣ REDIS → STREAM (CANDLE INPUT)
#                 # ---------------------------------
#                 exch_ts = safe_tick.get("exchange_timestamp")
#                 if not exch_ts:
#                     continue

#                 epoch_ts = int(
#                     datetime.fromisoformat(exch_ts)
#                     .astimezone(UTC)
#                     .timestamp()
#                 )

#                 token = safe_tick.get("instrument_token")
#                 price = safe_tick.get("last_price")

#                 if token is None or price is None:
#                     continue

#                 # ✅ CORRECT REDIS USAGE
#                 self.redis.xadd(
#                     f"tick_stream:{token}",
#                     {
#                         "ts": epoch_ts,
#                         "price": price,
#                         "volume": safe_tick.get("volume_traded", 0)
#                     }
#                 )

#             except Exception as e:
#                 log.exception(f"❌ on_ticks processing error: {e}")









# # app/market_ws.py

# import asyncio
# import logging
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# IST = ZoneInfo("Asia/Kolkata")
# UTC = ZoneInfo("UTC")


# class MarketWebSocket:
#     def __init__(
#         self,
#         api_key: str,
#         access_token: str,
#         broadcaster,
#         redis_client,
#         loop
#     ):
#         self.broadcaster = broadcaster
#         self.redis = redis_client
#         self.loop = loop

#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         # Zerodha ticker
#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#         print("✅ MarketWebSocket initialized")

#     # ==================================================
#     # START WS
#     # ==================================================
#     def start(self):
#         print("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # ==================================================
#     # CONNECT
#     # ==================================================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         print("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     # ==================================================
#     # CLOSE / ERROR
#     # ==================================================
#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         print(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         print(f"❌ Zerodha WS error: {code} | {reason}")

#     # ==================================================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # ==================================================
#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         print(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     # ==================================================
#     # SERIALIZATION
#     # ==================================================
#     def _serialize_value(self, v):
#         if isinstance(v, datetime):
#             return v.astimezone(IST).isoformat()
#         return v

#     def serialize_tick(self, tick: dict) -> dict:
#         safe = {}
#         for k, v in tick.items():
#             if isinstance(v, dict):
#                 safe[k] = {kk: self._serialize_value(vv) for kk, vv in v.items()}
#             else:
#                 safe[k] = self._serialize_value(v)
#         return safe

#     # ==================================================
#     # CORE: ON TICKS (🔥 LIVE MARKET PRINT HERE)
#     # ==================================================
#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         # 🔥 CONFIRM BATCH RECEIVED
#         print(f"🔥 LIVE MARKET TICK BATCH | count={len(ticks)}")

#         for raw_tick in ticks:
#             try:
#                 safe_tick = self.serialize_tick(raw_tick)

#                 token = safe_tick.get("instrument_token")
#                 price = safe_tick.get("last_price")
#                 exch_ts = safe_tick.get("exchange_timestamp")

#                 # 🔥 LIVE MARKET PRINT (BACKEND CONSOLE)
#                 print(
#                     f"📈 LIVE TICK | "
#                     f"token={token} | "
#                     f"price={price} | "
#                     f"time={exch_ts}"
#                 )

#                 # ---------------------------------
#                 # 1️⃣ UI → FULL JSON
#                 # ---------------------------------
#                 asyncio.run_coroutine_threadsafe(
#                     self.broadcaster.broadcast_tick(safe_tick),
#                     self.loop
#                 )

#                 # ---------------------------------
#                 # 2️⃣ REDIS → STREAM (CANDLE INPUT)
#                 # ---------------------------------
#                 if not exch_ts or token is None or price is None:
#                     continue

#                 epoch_ts = int(
#                     datetime.fromisoformat(exch_ts)
#                     .astimezone(UTC)
#                     .timestamp()
#                 )

#                 self.redis.xadd(
#                     f"tick_stream:{token}",
#                     {
#                         "ts": epoch_ts,
#                         "price": price,
#                         "volume": safe_tick.get("volume_traded", 0)
#                     }
#                 )

#             except Exception as e:
#                 print("❌ on_ticks error:", e)






# # app/market_ws.py

# import asyncio
# import json
# import logging
# from datetime import datetime
# from zoneinfo import ZoneInfo

# from kiteconnect import KiteTicker

# log = logging.getLogger("market_ws")

# IST = ZoneInfo("Asia/Kolkata")
# UTC = ZoneInfo("UTC")


# class MarketWebSocket:
#     def __init__(
#         self,
#         api_key: str,
#         access_token: str,
#         broadcaster,
#         redis_client,
#         loop
#     ):
#         self.broadcaster = broadcaster
#         self.redis = redis_client
#         self.loop = loop

#         self.subscribed_tokens = set()
#         self.ws_ready = False

#         # Zerodha WebSocket
#         self.ticker = KiteTicker(api_key, access_token)
#         self.ticker.on_connect = self.on_connect
#         self.ticker.on_ticks = self.on_ticks
#         self.ticker.on_close = self.on_close
#         self.ticker.on_error = self.on_error

#         print("✅ MarketWebSocket initialized")

#     # ==================================================
#     # START WS
#     # ==================================================
#     def start(self):
#         print("🟢 Starting Zerodha Market WebSocket")
#         self.ticker.connect(threaded=True)

#     # ==================================================
#     # CONNECT
#     # ==================================================
#     def on_connect(self, ws, response):
#         self.ws_ready = True
#         print("🟢 Zerodha WS connected")

#         if self.subscribed_tokens:
#             tokens = list(self.subscribed_tokens)
#             self.ticker.subscribe(tokens)
#             self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

#     # ==================================================
#     # CLOSE / ERROR
#     # ==================================================
#     def on_close(self, ws, code, reason):
#         self.ws_ready = False
#         print(f"🔴 Zerodha WS closed: {code} | {reason}")

#     def on_error(self, ws, code, reason):
#         print(f"❌ Zerodha WS error: {code} | {reason}")

#     # ==================================================
#     # SUBSCRIBE / UNSUBSCRIBE
#     # ==================================================
#     def subscribe(self, token: int):
#         token = int(token)
#         if token in self.subscribed_tokens:
#             return

#         self.subscribed_tokens.add(token)
#         print(f"🧲 SUBSCRIBE TOKEN: {token}")

#         if self.ws_ready:
#             self.ticker.subscribe([token])
#             self.ticker.set_mode(self.ticker.MODE_FULL, [token])

#     def unsubscribe(self, token: int):
#         token = int(token)
#         self.subscribed_tokens.discard(token)

#         if self.ws_ready:
#             self.ticker.unsubscribe([token])

#     # ==================================================
#     # SERIALIZATION
#     # ==================================================
#     def _serialize_value(self, v):
#         if isinstance(v, datetime):
#             return v.astimezone(IST).isoformat()
#         return v

#     def serialize_tick(self, tick: dict) -> dict:
#         """
#         Convert Zerodha raw tick to JSON-safe dict
#         """
#         safe = {}
#         for k, v in tick.items():
#             if isinstance(v, dict):
#                 safe[k] = {
#                     kk: self._serialize_value(vv)
#                     for kk, vv in v.items()
#                 }
#             else:
#                 safe[k] = self._serialize_value(v)
#         return safe

#     # ==================================================
#     # CORE: ON TICKS
#     # ==================================================
#     def on_ticks(self, ws, ticks):
#         if not ticks:
#             return

#         for raw_tick in ticks:
#             try:
#                 safe_tick = self.serialize_tick(raw_tick)

#                 # 🔥 FULL LIVE TICK JSON (BACKEND CONSOLE)
#                 print("🔥 LIVE FULL TICK JSON:")
#                 print(json.dumps(safe_tick, indent=2, ensure_ascii=False))

#                 # ---------------------------------
#                 # 1️⃣ UI → FULL JSON
#                 # ---------------------------------
#                 asyncio.run_coroutine_threadsafe(
#                     self.broadcaster.broadcast_tick(safe_tick),
#                     self.loop
#                 )

#                 # ---------------------------------
#                 # 2️⃣ REDIS → STREAM (CANDLE INPUT)
#                 # ---------------------------------
#                 exch_ts = safe_tick.get("exchange_timestamp")
#                 token = safe_tick.get("instrument_token")
#                 price = safe_tick.get("last_price")

#                 if not exch_ts or token is None or price is None:
#                     continue

#                 epoch_ts = int(
#                     datetime.fromisoformat(exch_ts)
#                     .astimezone(UTC)
#                     .timestamp()
#                 )

#                 self.redis.xadd(
#                     f"tick_stream:{token}",
#                     {
#                         "ts": epoch_ts,
#                         "price": price,
#                         "volume": safe_tick.get("volume_traded", 0)
#                     }
#                 )

#             except Exception as e:
#                 print("❌ on_ticks error:", e)








# app/market_ws.py

import asyncio
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from kiteconnect import KiteTicker

log = logging.getLogger("market_ws")

IST = ZoneInfo("Asia/Kolkata")


class MarketWebSocket:
    def __init__(
        self,
        api_key: str,
        access_token: str,
        broadcaster,
        redis_client,
        loop
    ):
        self.broadcaster = broadcaster
        self.redis = redis_client
        self.loop = loop

        self.subscribed_tokens = set()
        self.ws_ready = False

        # Zerodha WebSocket
        self.ticker = KiteTicker(api_key, access_token)
        self.ticker.on_connect = self.on_connect
        self.ticker.on_ticks = self.on_ticks
        self.ticker.on_close = self.on_close
        self.ticker.on_error = self.on_error

        log.info("✅ MarketWebSocket initialized")

    # ==================================================
    # START WS
    # ==================================================
    def start(self):
        log.info("🟢 Starting Zerodha Market WebSocket")
        self.ticker.connect(threaded=True)

    # ==================================================
    # CONNECT
    # ==================================================
    def on_connect(self, ws, response):
        self.ws_ready = True
        log.info("🟢 Zerodha WS connected")

        if self.subscribed_tokens:
            tokens = list(self.subscribed_tokens)
            self.ticker.subscribe(tokens)
            self.ticker.set_mode(self.ticker.MODE_FULL, tokens)

    # ==================================================
    # CLOSE / ERROR
    # ==================================================
    def on_close(self, ws, code, reason):
        self.ws_ready = False
        log.warning(f"🔴 Zerodha WS closed: {code} | {reason}")

    def on_error(self, ws, code, reason):
        log.error(f"❌ Zerodha WS error: {code} | {reason}")

    # ==================================================
    # SUBSCRIBE / UNSUBSCRIBE
    # ==================================================
    def subscribe(self, token: int):
        token = int(token)
        if token in self.subscribed_tokens:
            return

        self.subscribed_tokens.add(token)
        log.info(f"🧲 SUBSCRIBE TOKEN: {token}")

        if self.ws_ready:
            self.ticker.subscribe([token])
            self.ticker.set_mode(self.ticker.MODE_FULL, [token])

    def unsubscribe(self, token: int):
        token = int(token)
        self.subscribed_tokens.discard(token)

        if self.ws_ready:
            self.ticker.unsubscribe([token])

    # ==================================================
    # SERIALIZATION
    # ==================================================
    def _serialize_value(self, v):
        if isinstance(v, datetime):
            return v.astimezone(IST).isoformat()
        return v

    def serialize_tick(self, tick: dict) -> dict:
        """
        Convert Zerodha raw tick to JSON-safe dict
        """
        safe = {}
        for k, v in tick.items():
            if isinstance(v, dict):
                safe[k] = {
                    kk: self._serialize_value(vv)
                    for kk, vv in v.items()
                }
            else:
                safe[k] = self._serialize_value(v)
        return safe

    # ==================================================
    # CORE: ON TICKS
    # ==================================================
    def on_ticks(self, ws, ticks):
        if not ticks:
            return

        # 🔥 batch info
        log.info(f"🔥 LIVE MARKET TICK BATCH | count={len(ticks)}")

        for raw_tick in ticks:
            try:
                safe_tick = self.serialize_tick(raw_tick)

                # 🔥 FULL LIVE TICK JSON (BACKEND LOG)
                log.info("🔥 LIVE FULL TICK JSON:\n%s",
                         json.dumps(safe_tick, indent=2, ensure_ascii=False))

                # ---------------------------------
                # 1️⃣ UI → FULL JSON (NO DATA LOSS)
                # ---------------------------------
                asyncio.run_coroutine_threadsafe(
                    self.broadcaster.broadcast_tick(safe_tick),
                    self.loop
                )

                # ---------------------------------
                # 2️⃣ REDIS → STREAM (CANDLE INPUT)
                # ---------------------------------
                exch_ts = safe_tick.get("exchange_timestamp")
                token = safe_tick.get("instrument_token")
                price = safe_tick.get("last_price")

                if not exch_ts or token is None or price is None:
                    continue

                # ✅ CORRECT TIME HANDLING
                # Zerodha timestamp is already IST with offset
                epoch_ts = int(
                    datetime.fromisoformat(exch_ts).timestamp()
                )

                self.redis.xadd(
                    f"tick_stream:{token}",
                    {
                        "ts": epoch_ts,
                        "price": price,
                        "volume": safe_tick.get("volume_traded", 0)
                    }
                )

            except Exception as e:
                log.exception(f"❌ on_ticks processing error: {e}")

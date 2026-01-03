# app/market_ws_buffer.py

import json
import logging
import redis
from kiteconnect import KiteTicker
from sqlalchemy import text
from app.db import SessionLocal
from app.config import KITE_API_KEY

log = logging.getLogger("market_ws_buffer")
logging.basicConfig(level=logging.INFO)


# ===============================
# REDIS CONNECTION
# ===============================
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


class MarketWebSocketBuffer:
    """
    🔥 PURPOSE
    ----------
    Zerodha WebSocket → Live ticks → Redis (RAM buffer)

    ❌ No DB insert
    ❌ No candle logic
    ❌ No strategy

    ✔ Ultra fast
    ✔ Scalable
    ✔ Safe for 100k+ users
    """

    def __init__(self, access_token: str):
        self.kws = KiteTicker(KITE_API_KEY, access_token)
        self.subscribed_tokens = []

        self.kws.on_connect = self.on_connect
        self.kws.on_ticks = self.on_ticks
        self.kws.on_close = self.on_close
        self.kws.on_error = self.on_error

    # -----------------------------------------
    # FETCH TOP 50 INSTRUMENT TOKENS
    # -----------------------------------------
    def fetch_top_50_tokens(self):
        """
        Static selection:
        - Only BSE / BFO / CDS (as available now)
        - Sorted by instrument_token (stable)
        """

        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT instrument_token
                    FROM zerodha_broker_instrument
                    WHERE exchange IN ('BSE', 'BFO', 'CDS')
                    ORDER BY instrument_token
                    LIMIT 50
                """)
            ).fetchall()

            tokens = [r.instrument_token for r in rows]
            log.info("Fetched %s tokens for WS buffer", len(tokens))
            return tokens

        finally:
            db.close()

    # -----------------------------------------
    # WS EVENTS
    # -----------------------------------------
    def on_connect(self, ws, response):
        log.info("✅ Buffer WebSocket connected")

        self.subscribed_tokens = self.fetch_top_50_tokens()

        ws.subscribe(self.subscribed_tokens)
        ws.set_mode(ws.MODE_FULL, self.subscribed_tokens)

        log.info("📡 Subscribed to %s instruments (BUFFER MODE)", len(self.subscribed_tokens))

    def on_ticks(self, ws, ticks):
        """
        ticks example:
        {
          instrument_token,
          last_price,
          volume_traded_today,
          oi,
          ohlc,
          depth,
          exchange_timestamp
        }
        """

        for t in ticks:
            token = t["instrument_token"]

            payload = {
                "token": token,
                "ltp": t.get("last_price"),
                "volume": t.get("volume_traded_today"),
                "oi": t.get("oi"),
                "ohlc": t.get("ohlc"),
                "depth": t.get("depth"),
                "ts": str(t.get("exchange_timestamp"))
            }

            # 🔥 Redis key = tick:{instrument_token}
            redis_client.set(
                f"tick:{token}",
                json.dumps(payload)
            )

        log.debug("Buffered %s live ticks", len(ticks))

    def on_close(self, ws, code, reason):
        log.warning("❌ Buffer WS closed | %s | %s", code, reason)

    def on_error(self, ws, code, reason):
        log.error("🚨 Buffer WS error | %s | %s", code, reason)

    # -----------------------------------------
    def start(self):
        log.info("🚀 Starting Market WS Buffer (blocking)")
        self.kws.connect(threaded=False)

import os

ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY")
ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET")

TRADE_MODE = os.getenv("TRADE_MODE", "PAPER")

if TRADE_MODE == "LIVE":
    if not ZERODHA_API_KEY or not ZERODHA_API_SECRET:
        raise RuntimeError("❌ Zerodha keys required for LIVE mode")

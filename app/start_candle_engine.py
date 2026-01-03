import time
from app.candle_builder import build_1m_candles

print("🕯️ Candle Engine started")

while True:
    build_1m_candles()
    time.sleep(60)

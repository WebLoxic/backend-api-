import time
import json
import redis
import logging
from decimal import Decimal
from sqlalchemy import text
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_pnl")

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def run_live_pnl():
    logger.info("💰 Live P/L Tracker started")

    while True:
        try:
            db = SessionLocal()

            positions = db.execute(
                text("""
                    SELECT instrument_token, quantity, avg_price
                    FROM positions
                    WHERE status = 'OPEN'
                """)
            ).fetchall()

            if not positions:
                logger.info("⚠️ No OPEN positions")
                db.close()
                time.sleep(2)
                continue

            for token, qty, avg_price in positions:
                tick = r.get(f"tick:{token}")
                if not tick:
                    continue

                tick = json.loads(tick)
                ltp = tick.get("ltp") or tick.get("last_price")
                if ltp is None:
                    continue

                ltp = Decimal(str(ltp))
                qty = Decimal(qty)

                pnl = (ltp - avg_price) * qty

                print(
                    f"TOKEN {token} | QTY {qty} | "
                    f"AVG {avg_price} | LTP {ltp} | "
                    f"P/L {pnl:.2f}"
                )

            db.close()
            time.sleep(1)

        except Exception as e:
            logger.exception("🔥 Error in live P/L tracker")
            time.sleep(2)

if __name__ == "__main__":
    run_live_pnl()

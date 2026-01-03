import logging
import pytz
from datetime import datetime
from app.db import SessionLocal
from sqlalchemy import text

log = logging.getLogger("time_squareoff")

IST = pytz.timezone("Asia/Kolkata")

def run_time_squareoff():
    log.info("⏰ Time Square-off Engine started")

    now = datetime.now(IST)
    cutoff = now.replace(hour=15, minute=15, second=0, microsecond=0)

    if now < cutoff:
        return

    db = SessionLocal()

    positions = db.execute(text("""
        SELECT instrument_token, quantity, avg_price
        FROM positions
        WHERE status = 'OPEN'
    """)).fetchall()

    for token, qty, avg_price in positions:
        # Exit at market (price ignored, actual exit via Redis)
        db.execute(text("""
            UPDATE positions
            SET quantity = 0, status = 'CLOSED'
            WHERE instrument_token = :token
        """), {"token": token})

        log.warning("⏰ TIME SQUARE-OFF | TOKEN %s", token)

    db.commit()
    db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_time_squareoff()

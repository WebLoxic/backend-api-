import logging
from datetime import date
from app.db import SessionLocal
from sqlalchemy import text

log = logging.getLogger("daily_loss_guard")

MAX_DAILY_LOSS = -5000  # ₹

def run_daily_loss_guard():
    db = SessionLocal()

    today_pnl = db.execute(text("""
        SELECT COALESCE(SUM(realized_pnl),0)
        FROM trade_history
        WHERE DATE(exit_time) = CURRENT_DATE
    """)).scalar()

    log.info("📉 Today's P/L: %s", today_pnl)

    if today_pnl <= MAX_DAILY_LOSS:
        log.critical("🛑 KILL SWITCH TRIGGERED")

        db.execute(text("""
            UPDATE positions
            SET quantity = 0, status = 'CLOSED'
            WHERE status = 'OPEN'
        """))

        db.commit()

    db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_loss_guard()

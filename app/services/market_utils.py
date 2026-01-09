from sqlalchemy import text
from app.db import SessionLocal


def get_prev_day_close(token: int):
    """
    Returns previous trading day's close price.
    Assumes zerodha_candles_1m table already has historical data.
    """

    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT close
                FROM zerodha_candles_1m
                WHERE instrument_token = :token
                ORDER BY candle_time DESC
                OFFSET 1
                LIMIT 1
            """),
            {"token": token}
        ).first()

        return row.close if row else None

    finally:
        db.close()

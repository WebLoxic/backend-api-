from sqlalchemy import text
from app.db import SessionLocal

def simple_ma_strategy(token: int):
    db = SessionLocal()

    rows = db.execute(
        text("""
            SELECT close
            FROM candles_1m
            WHERE instrument_token = :token
            ORDER BY candle_time DESC
            LIMIT 5
        """),
        {"token": token}
    ).fetchall()

    closes = [r.close for r in rows]

    if len(closes) < 5:
        return None

    avg = sum(closes) / len(closes)

    if closes[0] > avg:
        return "BUY"
    elif closes[0] < avg:
        return "SELL"

from decimal import Decimal
from sqlalchemy import text
from app.db import SessionLocal
import logging

log = logging.getLogger("paper_executor")


def place_order(
    *,
    user_id: int,
    instrument_token: int,
    symbol: str,
    exchange: str,
    side: str,
    quantity: int,
    price: Decimal
) -> dict:
    log.info(
        f"🟡 PAPER ORDER | {side} | {symbol} | QTY {quantity} @ {price}"
    )

    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO positions (
                    user_id,
                    instrument_token,
                    symbol,
                    exchange,
                    quantity,
                    avg_price,
                    side,
                    status,
                    created_at
                )
                VALUES (
                    :uid,
                    :token,
                    :symbol,
                    :exchange,
                    :qty,
                    :price,
                    :side,
                    'OPEN',
                    now()
                )
            """),
            {
                "uid": user_id,
                "token": instrument_token,
                "symbol": symbol,
                "exchange": exchange,
                "qty": quantity,
                "price": price,
                "side": side,
            }
        )
        db.commit()

        return {
            "order_id": f"PAPER-{instrument_token}",
            "status": "FILLED",
            "filled_price": price,
        }

    finally:
        db.close()

from kiteconnect import KiteConnect
from sqlalchemy import text
from decimal import Decimal
from app.db import SessionLocal
from app.settings import ZERODHA_API_KEY
import logging

log = logging.getLogger("zerodha_executor")


# ------------------------------------------------
# GET AUTHENTICATED KITE (PER USER)
# ------------------------------------------------
def get_kite_for_user(user_id: int) -> KiteConnect:
    db = SessionLocal()
    try:
        access_token = db.execute(
            text("""
                SELECT access_token
                FROM zerodha_broker_tokens
                WHERE user_id = :uid
                  AND is_active = true
                ORDER BY generated_at DESC
                LIMIT 1
            """),
            {"uid": user_id}
        ).scalar()

        if not access_token:
            raise RuntimeError("❌ No active Zerodha token found")

        kite = KiteConnect(api_key=ZERODHA_API_KEY)
        kite.set_access_token(access_token)
        return kite

    finally:
        db.close()


# ------------------------------------------------
# PLACE REAL ORDER
# ------------------------------------------------
def place_order(
    *,
    user_id: int,
    instrument_token: int,
    symbol: str,
    exchange: str,
    side: str,          # BUY | SELL
    quantity: int,
    product: str = "MIS"
) -> dict:
    kite = get_kite_for_user(user_id)

    log.info(
        f"🔵 REAL ORDER | {side} | {symbol} | QTY {quantity}"
    )

    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=exchange,
        tradingsymbol=symbol,
        transaction_type=(
            kite.TRANSACTION_TYPE_BUY
            if side == "BUY"
            else kite.TRANSACTION_TYPE_SELL
        ),
        quantity=int(quantity),
        order_type=kite.ORDER_TYPE_MARKET,
        product=product,
    )

    order = kite.order_history(order_id)[-1]

    return {
        "order_id": order_id,
        "status": order["status"],
        "filled_price": Decimal(order["average_price"] or 0),
        "exchange_time": order["exchange_timestamp"],
    }

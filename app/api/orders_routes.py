

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from decimal import Decimal
import redis, json, time
from app.db import SessionLocal
from app.settings import TRADE_MODE

# Broker executors
if TRADE_MODE == "LIVE":
    from app.broker.zerodha_executor import place_order
else:
    from app.broker.paper_executor import place_order


router = APIRouter(prefix="/orders", tags=["Orders"])

# Redis (live ticks)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# -------------------------------------------------
# 🔹 MANUAL BUY ORDER
# -------------------------------------------------
@router.post("/buy")
def manual_buy(
    user_id: int,
    instrument_token: int,
    symbol: str,
    exchange: str,
    quantity: int,
):
    if quantity <= 0:
        raise HTTPException(400, "Quantity must be > 0")

    tick = r.get(f"tick:{instrument_token}")
    if not tick:
        raise HTTPException(400, "Live price not available")

    tick = json.loads(tick)
    ltp = Decimal(str(tick.get("ltp") or tick.get("last_price")))

    db = SessionLocal()
    try:
        # Place order (paper / live)
        result = place_order(
            token=instrument_token,
            symbol=symbol,
            exchange=exchange,
            side="BUY",
            qty=quantity,
            price=ltp,
        )

        if result["status"] != "COMPLETE":
            raise HTTPException(400, "Order failed")

        fill_price = Decimal(str(result["filled_price"]))

        # Upsert position
        db.execute(
            text("""
                INSERT INTO positions (
                    user_id, instrument_token, symbol, exchange,
                    quantity, avg_price, status, opened_at
                )
                VALUES (
                    :uid, :token, :symbol, :exchange,
                    :qty, :price, 'OPEN', now()
                )
                ON CONFLICT (user_id, instrument_token)
                DO UPDATE SET
                    avg_price = (
                        (positions.avg_price * positions.quantity + :price * :qty)
                        / (positions.quantity + :qty)
                    ),
                    quantity = positions.quantity + :qty,
                    updated_at = now()
            """),
            {
                "uid": user_id,
                "token": instrument_token,
                "symbol": symbol,
                "exchange": exchange,
                "qty": quantity,
                "price": fill_price,
            }
        )

        db.commit()

        return {
            "status": "BUY_EXECUTED",
            "symbol": symbol,
            "quantity": quantity,
            "price": float(fill_price),
            "amount": float(fill_price * quantity),
        }

    finally:
        db.close()


# -------------------------------------------------
# 🔹 SELL PREVIEW (P/L BEFORE SELL)
# -------------------------------------------------
@router.post("/preview-sell")
def preview_sell(
    user_id: int,
    instrument_token: int,
    quantity: int,
):
    db = SessionLocal()
    try:
        pos = db.execute(
            text("""
                SELECT quantity, avg_price
                FROM positions
                WHERE user_id = :uid
                  AND instrument_token = :token
                  AND status = 'OPEN'
            """),
            {"uid": user_id, "token": instrument_token}
        ).fetchone()

        if not pos:
            raise HTTPException(400, "No open position found")

        available_qty, avg_price = pos

        if quantity > available_qty:
            raise HTTPException(400, "Sell quantity exceeds holding")

        tick = r.get(f"tick:{instrument_token}")
        if not tick:
            raise HTTPException(400, "Live price not available")

        tick = json.loads(tick)
        ltp = Decimal(str(tick.get("ltp") or tick.get("last_price")))
        avg_price = Decimal(str(avg_price))
        quantity = Decimal(str(quantity))

        pnl = (ltp - avg_price) * quantity
        pnl_pct = ((ltp - avg_price) / avg_price) * 100

        return {
            "instrument_token": instrument_token,
            "sell_qty": int(quantity),
            "avg_buy_price": float(avg_price),
            "current_price": float(ltp),
            "expected_pnl": float(pnl),
            "pnl_percent": float(round(pnl_pct, 2)),
            "status": "PROFIT" if pnl > 0 else "LOSS",
        }

    finally:
        db.close()


# -------------------------------------------------
# 🔹 CONFIRM SELL (ACTUAL EXECUTION)
# -------------------------------------------------
@router.post("/sell")
def confirm_sell(
    user_id: int,
    instrument_token: int,
    symbol: str,
    exchange: str,
    quantity: int,
):
    db = SessionLocal()
    try:
        pos = db.execute(
            text("""
                SELECT id, quantity, avg_price, opened_at
                FROM positions
                WHERE user_id = :uid
                  AND instrument_token = :token
                  AND status = 'OPEN'
            """),
            {"uid": user_id, "token": instrument_token}
        ).fetchone()

        if not pos:
            raise HTTPException(400, "No open position")

        pos_id, available_qty, avg_price, entry_time = pos

        if quantity > available_qty:
            raise HTTPException(400, "Sell quantity exceeds holding")

        tick = r.get(f"tick:{instrument_token}")
        if not tick:
            raise HTTPException(400, "Live price not available")

        tick = json.loads(tick)
        ltp = Decimal(str(tick.get("ltp") or tick.get("last_price")))

        # Place SELL order
        result = place_order(
            token=instrument_token,
            symbol=symbol,
            exchange=exchange,
            side="SELL",
            qty=quantity,
            price=ltp,
        )

        if result["status"] != "COMPLETE":
            raise HTTPException(400, "Sell order failed")

        fill_price = Decimal(str(result["filled_price"]))

        realized_pnl = (fill_price - Decimal(avg_price)) * Decimal(quantity)
        pnl_pct = ((fill_price - Decimal(avg_price)) / Decimal(avg_price)) * 100

        # Update position
        new_qty = available_qty - quantity
        new_status = "CLOSED" if new_qty == 0 else "OPEN"

        db.execute(
            text("""
                UPDATE positions
                SET quantity = :q,
                    status = :status,
                    updated_at = now()
                WHERE id = :id
            """),
            {"q": new_qty, "status": new_status, "id": pos_id}
        )

        # Insert trade history
        db.execute(
            text("""
                INSERT INTO trade_history (
                    user_id,
                    instrument_token, symbol, exchange,
                    side,
                    entry_price, exit_price,
                    quantity,
                    realized_pnl, pnl_percent,
                    entry_time, exit_time,
                    exit_reason
                )
                VALUES (
                    :uid,
                    :token, :symbol, :exchange,
                    'SELL',
                    :entry_price, :exit_price,
                    :qty,
                    :pnl, :pnl_pct,
                    :entry_time, now(),
                    'MANUAL_SELL'
                )
            """),
            {
                "uid": user_id,
                "token": instrument_token,
                "symbol": symbol,
                "exchange": exchange,
                "entry_price": avg_price,
                "exit_price": fill_price,
                "qty": quantity,
                "pnl": realized_pnl,
                "pnl_pct": pnl_pct,
                "entry_time": entry_time,
            }
        )

        db.commit()

        return {
            "status": "SELL_EXECUTED",
            "symbol": symbol,
            "quantity": quantity,
            "exit_price": float(fill_price),
            "realized_pnl": float(realized_pnl),
        }

    finally:
        db.close()


# -------------------------------------------------
# 🔹 USER TRADE HISTORY
# -------------------------------------------------
@router.get("/history")
def trade_history(user_id: int):
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT
                    instrument_token, symbol, exchange,
                    side, quantity,
                    entry_price, exit_price,
                    realized_pnl, pnl_percent,
                    entry_time, exit_time
                FROM trade_history
                WHERE user_id = :uid
                ORDER BY exit_time DESC
                LIMIT 100
            """),
            {"uid": user_id}
        ).fetchall()

        return [dict(r) for r in rows]

    finally:
        db.close()

from sqlalchemy import text
from decimal import Decimal
from app.db import SessionLocal


def get_user_risk(user_id: int):
    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT capital, risk_per_trade_pct,
                   max_daily_loss_pct, max_open_positions,
                   trading_enabled
            FROM user_risk_settings
            WHERE user_id = :uid
        """), {"uid": user_id}).fetchone()

        if not row:
            raise Exception("Risk profile missing")

        return row
    finally:
        db.close()


def calculate_quantity(user_id, price: Decimal, sl_pct=Decimal("1")):
    capital, risk_pct, *_ = get_user_risk(user_id)

    capital = Decimal(str(capital))
    risk_amount = capital * Decimal(risk_pct) / 100
    loss_per_qty = price * sl_pct / 100

    if loss_per_qty <= 0:
        return 0

    qty = int(risk_amount / loss_per_qty)
    return max(qty, 1)


def check_daily_loss(user_id):
    db = SessionLocal()
    try:
        capital, _, max_daily_loss_pct, *_ = get_user_risk(user_id)

        pnl = db.execute(text("""
            SELECT COALESCE(SUM(realized_pnl),0)
            FROM trade_history
            WHERE user_id = :uid
              AND exit_time::date = CURRENT_DATE
        """), {"uid": user_id}).scalar()

        max_loss = Decimal(capital) * Decimal(max_daily_loss_pct) / 100

        return Decimal(pnl) <= -max_loss
    finally:
        db.close()


def kill_switch(user_id):
    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE user_risk_settings
            SET trading_enabled = false,
                updated_at = now()
            WHERE user_id = :uid
        """), {"uid": user_id})
        db.commit()
    finally:
        db.close()

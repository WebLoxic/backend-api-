import logging
from sqlalchemy import text
from app.db import engine

log = logging.getLogger("order_engine")
QTY = 1


def process_orders():
    with engine.begin() as conn:
        signals = conn.execute(
            text("""
                SELECT *
                FROM strategy_signals
                WHERE id NOT IN (
                    SELECT signal_id FROM paper_orders
                )
            """)
        ).fetchall()

        for s in signals:
            pos = conn.execute(
                text("SELECT * FROM positions WHERE instrument_token=:t"),
                {"t": s.instrument_token}
            ).fetchone()

            if s.signal == "BUY" and not pos:
                conn.execute(
                    text("""
                        INSERT INTO positions VALUES (:t,:q,:p,now())
                    """),
                    {"t": s.instrument_token, "q": QTY, "p": s.price}
                )

                conn.execute(
                    text("""
                        INSERT INTO paper_orders
                        (instrument_token, side, quantity, entry_price)
                        VALUES (:t,'BUY',:q,:p)
                    """),
                    {"t": s.instrument_token, "q": QTY, "p": s.price}
                )

            elif s.signal == "SELL" and pos:
                pnl = (s.price - pos.avg_price) * pos.quantity

                conn.execute(
                    text("DELETE FROM positions WHERE instrument_token=:t"),
                    {"t": s.instrument_token}
                )

                conn.execute(
                    text("""
                        INSERT INTO pnl_ledger
                        (instrument_token, realized_pnl, unrealized_pnl)
                        VALUES (:t,:r,0)
                    """),
                    {"t": s.instrument_token, "r": pnl}
                )

                conn.execute(
                    text("""
                        INSERT INTO paper_orders
                        (instrument_token, side, quantity, entry_price, status)
                        VALUES (:t,'SELL',:q,:p,'CLOSED')
                    """),
                    {"t": s.instrument_token, "q": pos.quantity, "p": s.price}
                )

                log.info("💰 P/L booked token=%s pnl=%s", s.instrument_token, pnl)

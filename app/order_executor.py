# import time
# import logging
# from decimal import Decimal
# from sqlalchemy import text

# from app.db import SessionLocal
# from app.settings import TRADE_MODE
# from app.utils.quantity_calculator import calculate_quantity

# # ---------------- BROKER SWITCH ----------------
# if TRADE_MODE == "LIVE":
#     from app.broker.zerodha_executor import place_order
# else:
#     from app.broker.paper_executor import place_order

# # ---------------- CONFIG ----------------
# CHECK_INTERVAL = 1  # seconds

# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger("order_executor")


# def run_order_executor():
#     log.info(f"🧠 Order Executor started | MODE={TRADE_MODE}")

#     while True:
#         db = SessionLocal()
#         try:
#             # -------------------------------------------------
#             # 1️⃣ Fetch unprocessed strategy signals
#             # -------------------------------------------------
#             signals = db.execute(text("""
#                 SELECT
#                     s.id,
#                     s.user_id,
#                     s.instrument_token,
#                     s.strategy_name,
#                     s.signal,
#                     s.price
#                 FROM strategy_signals s
#                 WHERE s.processed = false
#                 ORDER BY s.created_at
#             """)).fetchall()

#             for (
#                 sig_id,
#                 user_id,
#                 token,
#                 strategy,
#                 side,
#                 signal_price
#             ) in signals:

#                 # -------------------------------------------------
#                 # 2️⃣ Check USER AUTO MODE
#                 # -------------------------------------------------
#                 auto_mode = db.execute(text("""
#                     SELECT auto_mode
#                     FROM user_trading_settings
#                     WHERE user_id = :uid
#                 """), {"uid": user_id}).scalar()

#                 if not auto_mode:
#                     log.info(
#                         "⏭️ AUTO MODE OFF | user=%s | signal ignored",
#                         user_id
#                     )
#                     db.execute(
#                         text("UPDATE strategy_signals SET processed=true WHERE id=:id"),
#                         {"id": sig_id}
#                     )
#                     db.commit()
#                     continue

#                 # -------------------------------------------------
#                 # 3️⃣ Fetch USER RISK SETTINGS
#                 # -------------------------------------------------
#                 settings = db.execute(text("""
#                     SELECT capital, risk_percent
#                     FROM user_trading_settings
#                     WHERE user_id = :uid
#                 """), {"uid": user_id}).fetchone()

#                 if not settings:
#                     log.warning("⚠️ No trading settings | user=%s", user_id)
#                     continue

#                 capital, risk_pct = settings
#                 capital = Decimal(str(capital))
#                 risk_pct = Decimal(str(risk_pct))
#                 entry_price = Decimal(str(signal_price))

#                 # -------------------------------------------------
#                 # 4️⃣ Calculate Quantity (Risk Based)
#                 # -------------------------------------------------
#                 qty = calculate_quantity(
#                     capital=capital,
#                     risk_percent=risk_pct,
#                     entry_price=entry_price
#                 )

#                 if qty <= 0:
#                     log.warning(
#                         "⚠️ Quantity zero | user=%s token=%s",
#                         user_id, token
#                     )
#                     continue

#                 # -------------------------------------------------
#                 # 5️⃣ Place Order (PAPER / LIVE)
#                 # -------------------------------------------------
#                 result = place_order(
#                     token=token,
#                     symbol="AUTO",
#                     exchange="AUTO",
#                     side=side,
#                     qty=qty,
#                     price=entry_price
#                 )

#                 if result.get("status") != "COMPLETE":
#                     log.warning(
#                         "❌ Order failed | user=%s token=%s",
#                         user_id, token
#                     )
#                     continue

#                 fill_price = Decimal(str(result["filled_price"]))

#                 # -------------------------------------------------
#                 # 6️⃣ Update / Create POSITION
#                 # -------------------------------------------------
#                 if side == "BUY":
#                     db.execute(text("""
#                         INSERT INTO positions (
#                             user_id,
#                             instrument_token,
#                             symbol,
#                             exchange,
#                             quantity,
#                             avg_price,
#                             status,
#                             updated_at
#                         )
#                         VALUES (
#                             :uid,
#                             :token,
#                             'AUTO',
#                             'AUTO',
#                             :qty,
#                             :price,
#                             'OPEN',
#                             now()
#                         )
#                         ON CONFLICT (user_id, instrument_token)
#                         DO UPDATE SET
#                             avg_price =
#                                 ((positions.avg_price * positions.quantity)
#                                 + (:price * :qty))
#                                 / (positions.quantity + :qty),
#                             quantity = positions.quantity + :qty,
#                             updated_at = now()
#                     """), {
#                         "uid": user_id,
#                         "token": token,
#                         "qty": qty,
#                         "price": fill_price
#                     })

#                 elif side == "SELL":
#                     # SELL signal = exit (simple logic)
#                     db.execute(text("""
#                         UPDATE positions
#                         SET
#                             quantity = 0,
#                             status = 'CLOSED',
#                             updated_at = now()
#                         WHERE user_id = :uid
#                           AND instrument_token = :token
#                           AND status = 'OPEN'
#                     """), {
#                         "uid": user_id,
#                         "token": token
#                     })

#                 # -------------------------------------------------
#                 # 7️⃣ Mark signal as processed
#                 # -------------------------------------------------
#                 db.execute(text("""
#                     UPDATE strategy_signals
#                     SET processed = true
#                     WHERE id = :id
#                 """), {"id": sig_id})

#                 db.commit()

#                 log.info(
#                     "✅ ORDER EXECUTED | user=%s | %s | token=%s | qty=%s @ %s",
#                     user_id, side, token, qty, fill_price
#                 )

#         except Exception as e:
#             db.rollback()
#             log.error("🔥 Order executor error", exc_info=e)

#         finally:
#             db.close()

#         time.sleep(CHECK_INTERVAL)


# if __name__ == "__main__":
#     run_order_executor()




import time
import logging
from decimal import Decimal
from sqlalchemy import text

from app.db import SessionLocal
from app.settings import TRADE_MODE
from app.utils.quantity_calculator import calculate_quantity

# ---------------- BROKER SWITCH ----------------
if TRADE_MODE == "LIVE":
    from app.broker.zerodha_executor import place_order
else:
    from app.broker.paper_executor import place_order

# ---------------- CONFIG ----------------
CHECK_INTERVAL = 1  # seconds

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("order_executor")


# =====================================================
# 🔥 MANUAL ORDER EXECUTOR (API USE)
# =====================================================
def execute_order(
    *,
    user_id: int,
    instrument_token: int,
    side: str,
    quantity: int,
    source: str = "MANUAL",
):
    """
    Manual order execution
    Used by manual_orders_routes.py
    """

    log.info(
        "✋ MANUAL ORDER | user=%s | side=%s | token=%s | qty=%s",
        user_id,
        side,
        instrument_token,
        quantity,
    )

    result = place_order(
        token=instrument_token,
        symbol="MANUAL",
        exchange="MANUAL",
        side=side,
        qty=quantity,
        price=None,
    )

    return result


# =====================================================
# 🧠 AUTO STRATEGY ORDER EXECUTOR (BACKGROUND LOOP)
# =====================================================
def run_order_executor():
    log.info(f"🧠 Order Executor started | MODE={TRADE_MODE}")

    while True:
        db = SessionLocal()
        try:
            # -------------------------------------------------
            # 1️⃣ Fetch unprocessed strategy signals
            # -------------------------------------------------
            signals = db.execute(text("""
                SELECT
                    s.id,
                    s.user_id,
                    s.instrument_token,
                    s.strategy_name,
                    s.signal,
                    s.price
                FROM strategy_signals s
                WHERE s.processed = false
                ORDER BY s.created_at
            """)).fetchall()

            for (
                sig_id,
                user_id,
                token,
                strategy,
                side,
                signal_price
            ) in signals:

                # -------------------------------------------------
                # 2️⃣ Check USER AUTO MODE
                # -------------------------------------------------
                auto_mode = db.execute(text("""
                    SELECT auto_mode
                    FROM user_trading_settings
                    WHERE user_id = :uid
                """), {"uid": user_id}).scalar()

                if not auto_mode:
                    log.info(
                        "⏭️ AUTO MODE OFF | user=%s | signal ignored",
                        user_id
                    )
                    db.execute(
                        text("UPDATE strategy_signals SET processed=true WHERE id=:id"),
                        {"id": sig_id}
                    )
                    db.commit()
                    continue

                # -------------------------------------------------
                # 3️⃣ Fetch USER RISK SETTINGS
                # -------------------------------------------------
                settings = db.execute(text("""
                    SELECT capital, risk_percent
                    FROM user_trading_settings
                    WHERE user_id = :uid
                """), {"uid": user_id}).fetchone()

                if not settings:
                    log.warning("⚠️ No trading settings | user=%s", user_id)
                    continue

                capital, risk_pct = settings
                capital = Decimal(str(capital))
                risk_pct = Decimal(str(risk_pct))
                entry_price = Decimal(str(signal_price))

                # -------------------------------------------------
                # 4️⃣ Calculate Quantity (Risk Based)
                # -------------------------------------------------
                qty = calculate_quantity(
                    capital=capital,
                    risk_percent=risk_pct,
                    entry_price=entry_price
                )

                if qty <= 0:
                    log.warning(
                        "⚠️ Quantity zero | user=%s token=%s",
                        user_id, token
                    )
                    continue

                # -------------------------------------------------
                # 5️⃣ Place Order (PAPER / LIVE)
                # -------------------------------------------------
                result = place_order(
                    token=token,
                    symbol="AUTO",
                    exchange="AUTO",
                    side=side,
                    qty=qty,
                    price=entry_price
                )

                if result.get("status") != "COMPLETE":
                    log.warning(
                        "❌ Order failed | user=%s token=%s",
                        user_id, token
                    )
                    continue

                fill_price = Decimal(str(result["filled_price"]))

                # -------------------------------------------------
                # 6️⃣ Update / Create POSITION
                # -------------------------------------------------
                if side == "BUY":
                    db.execute(text("""
                        INSERT INTO positions (
                            user_id,
                            instrument_token,
                            symbol,
                            exchange,
                            quantity,
                            avg_price,
                            status,
                            updated_at
                        )
                        VALUES (
                            :uid,
                            :token,
                            'AUTO',
                            'AUTO',
                            :qty,
                            :price,
                            'OPEN',
                            now()
                        )
                        ON CONFLICT (user_id, instrument_token)
                        DO UPDATE SET
                            avg_price =
                                ((positions.avg_price * positions.quantity)
                                + (:price * :qty))
                                / (positions.quantity + :qty),
                            quantity = positions.quantity + :qty,
                            updated_at = now()
                    """), {
                        "uid": user_id,
                        "token": token,
                        "qty": qty,
                        "price": fill_price
                    })

                elif side == "SELL":
                    db.execute(text("""
                        UPDATE positions
                        SET
                            quantity = 0,
                            status = 'CLOSED',
                            updated_at = now()
                        WHERE user_id = :uid
                          AND instrument_token = :token
                          AND status = 'OPEN'
                    """), {
                        "uid": user_id,
                        "token": token
                    })

                # -------------------------------------------------
                # 7️⃣ Mark signal as processed
                # -------------------------------------------------
                db.execute(text("""
                    UPDATE strategy_signals
                    SET processed = true
                    WHERE id = :id
                """), {"id": sig_id})

                db.commit()

                log.info(
                    "✅ ORDER EXECUTED | user=%s | %s | token=%s | qty=%s @ %s",
                    user_id, side, token, qty, fill_price
                )

        except Exception as e:
            db.rollback()
            log.error("🔥 Order executor error", exc_info=e)

        finally:
            db.close()

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_order_executor()

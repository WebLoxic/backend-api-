# import time
# import json
# import logging
# import redis
# from decimal import Decimal
# from sqlalchemy import text
# from app.db import SessionLocal

# # ---------------- CONFIG ----------------
# TARGET_PCT = Decimal("2.0")     # +2%
# STOPLOSS_PCT = Decimal("-1.0")  # -1%
# SLEEP_SECONDS = 1

# # ----------------------------------------
# logging.basicConfig(level=logging.INFO)
# log = logging.getLogger("auto_squareoff")

# r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# def run_auto_squareoff():
#     log.info("🚨 Auto Square-off Engine started")

#     while True:
#         db = SessionLocal()
#         try:
#             positions = db.execute(
#                 text("""
#                     SELECT id, instrument_token, quantity, avg_price
#                     FROM positions
#                     WHERE status = 'OPEN'
#                 """)
#             ).fetchall()

#             for pos_id, token, qty, avg_price in positions:
#                 if qty <= 0:
#                     continue

#                 tick = r.get(f"tick:{token}")
#                 if not tick:
#                     continue

#                 tick = json.loads(tick)
#                 ltp = tick.get("ltp") or tick.get("last_price")

#                 if ltp is None:
#                     continue

#                 # Decimal safety
#                 ltp = Decimal(str(ltp))
#                 avg_price = Decimal(avg_price)

#                 pnl_pct = ((ltp - avg_price) / avg_price) * 100

#                 log.info(
#                     f"TOKEN {token} | QTY {qty} | AVG {avg_price} | "
#                     f"LTP {ltp} | P/L % {pnl_pct:.2f}"
#                 )

#                 # -------- EXIT CONDITIONS --------
#                 if pnl_pct >= TARGET_PCT or pnl_pct <= STOPLOSS_PCT:
#                     reason = "TARGET HIT" if pnl_pct >= TARGET_PCT else "STOPLOSS HIT"

#                     log.warning(
#                         f"🚨 SQUARE-OFF | {reason} | TOKEN {token} | P/L % {pnl_pct:.2f}"
#                     )

#                     db.execute(
#                         text("""
#                             UPDATE positions
#                             SET
#                                 quantity = 0,
#                                 status = 'CLOSED',
#                                 updated_at = now()
#                             WHERE id = :id
#                         """),
#                         {"id": pos_id}
#                     )

#                     db.commit()

#         except Exception as e:
#             log.error("🔥 Error in auto square-off engine", exc_info=e)
#             db.rollback()

#         finally:
#             db.close()

#         time.sleep(SLEEP_SECONDS)


# if __name__ == "__main__":
#     run_auto_squareoff()


import time
import json
import logging
import redis
from decimal import Decimal
from sqlalchemy import text
from app.db import SessionLocal

# ================= CONFIG =================
TARGET_PCT = Decimal("2.0")      # +2% target
STOPLOSS_PCT = Decimal("-1.0")   # -1% stoploss
SLEEP_SECONDS = 1
# ========================================

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auto_squareoff")

# Redis (ticks from websocket)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)


def run_auto_squareoff():
    log.info("🚨 Auto Square-off Engine started")

    while True:
        db = SessionLocal()

        try:
            # 🔥 ONLY REAL REQUIRED FIELDS
            positions = db.execute(
                text("""
                    SELECT
                        id,
                        instrument_token,
                        quantity,
                        avg_price,
                        opened_at
                    FROM positions
                    WHERE status = 'OPEN'
                """)
            ).fetchall()

            for pos_id, token, qty, avg_price, entry_time in positions:

                if qty <= 0:
                    continue

                # -------- LIVE PRICE --------
                tick = r.get(f"tick:{token}")
                if not tick:
                    continue

                tick = json.loads(tick)
                ltp = tick.get("ltp") or tick.get("last_price")
                if ltp is None:
                    continue

                # -------- DECIMAL SAFETY --------
                ltp = Decimal(str(ltp))
                avg_price = Decimal(str(avg_price))
                qty = Decimal(str(qty))

                pnl = (ltp - avg_price) * qty
                pnl_pct = ((ltp - avg_price) / avg_price) * 100

                log.info(
                    f"TOKEN {token} | QTY {qty} | AVG {avg_price} | "
                    f"LTP {ltp} | P/L % {pnl_pct:.2f}"
                )

                # -------- EXIT CONDITIONS --------
                if pnl_pct >= TARGET_PCT or pnl_pct <= STOPLOSS_PCT:

                    reason = "TARGET" if pnl_pct >= TARGET_PCT else "STOPLOSS"

                    log.warning(
                        f"🚨 SQUARE-OFF | {reason} | TOKEN {token} | "
                        f"P/L % {pnl_pct:.2f}"
                    )

                    # -------- GET REAL SYMBOL / EXCHANGE --------
                    inst = db.execute(
                        text("""
                            SELECT tradingsymbol, exchange
                            FROM instrument_master
                            WHERE instrument_token = :token
                        """),
                        {"token": token}
                    ).fetchone()

                    symbol = inst.tradingsymbol if inst else None
                    exchange = inst.exchange if inst else None

                    # -------- CLOSE POSITION --------
                    db.execute(
                        text("""
                            UPDATE positions
                            SET
                                quantity = 0,
                                status = 'CLOSED',
                                updated_at = now()
                            WHERE id = :id
                        """),
                        {"id": pos_id}
                    )

                    # -------- INSERT TRADE HISTORY --------
                    db.execute(
                        text("""
                            INSERT INTO trade_history (
                                instrument_token,
                                symbol,
                                exchange,
                                side,
                                entry_price,
                                exit_price,
                                quantity,
                                realized_pnl,
                                pnl_percent,
                                entry_time,
                                exit_time,
                                exit_reason
                            )
                            VALUES (
                                :token,
                                :symbol,
                                :exchange,
                                'BUY',
                                :entry_price,
                                :exit_price,
                                :qty,
                                :pnl,
                                :pnl_pct,
                                :entry_time,
                                now(),
                                :reason
                            )
                        """),
                        {
                            "token": token,
                            "symbol": symbol,
                            "exchange": exchange,
                            "entry_price": avg_price,
                            "exit_price": ltp,
                            "qty": qty,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "entry_time": entry_time,
                            "reason": reason,
                        }
                    )

                    db.commit()

        except Exception as e:
            db.rollback()
            log.error("🔥 Error in auto square-off engine", exc_info=e)

        finally:
            db.close()

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    run_auto_squareoff()

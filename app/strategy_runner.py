# import logging
# import pandas as pd
# from sqlalchemy import text
# from app.db import engine

# log = logging.getLogger("strategy_runner")

# # -----------------------------
# # CONFIG
# # -----------------------------
# STRATEGY_NAME = "EMA_9_21"
# FAST_EMA = 9
# SLOW_EMA = 21
# CANDLE_LIMIT = 100  # enough for EMA stability


# # -----------------------------
# # EMA CALC
# # -----------------------------
# def calculate_ema(series, period):
#     return series.ewm(span=period, adjust=False).mean()


# # -----------------------------
# # MAIN STRATEGY RUNNER
# # -----------------------------
# def run_ema_strategy():
#     log.info("🚀 EMA Strategy Runner started")

#     with engine.connect() as conn:

#         # 1️⃣ Active instruments (top 50)
#         instruments = conn.execute(
#             text("""
#                 SELECT DISTINCT instrument_token
#                 FROM zerodha_candles_1m
#                 ORDER BY instrument_token
#                 LIMIT 50
#             """)
#         ).fetchall()

#         log.info("📊 Instruments found for strategy: %s", len(instruments))

#         for row in instruments:
#             token = row.instrument_token

#             # 2️⃣ Load candles
#             candles_df = pd.read_sql(
#                 text("""
#                     SELECT candle_time, close
#                     FROM zerodha_candles_1m
#                     WHERE instrument_token = :token
#                     ORDER BY candle_time DESC
#                     LIMIT :limit
#                 """),
#                 conn,
#                 params={"token": token, "limit": CANDLE_LIMIT}
#             )

#             if len(candles_df) < SLOW_EMA:
#                 continue  # not enough data

#             candles_df = candles_df.sort_values("candle_time")

#             # 3️⃣ EMA calculation
#             candles_df["ema_fast"] = calculate_ema(candles_df["close"], FAST_EMA)
#             candles_df["ema_slow"] = calculate_ema(candles_df["close"], SLOW_EMA)

#             prev = candles_df.iloc[-2]
#             curr = candles_df.iloc[-1]

#             signal = None

#             # 4️⃣ EMA crossover logic
#             if prev.ema_fast < prev.ema_slow and curr.ema_fast > curr.ema_slow:
#                 signal = "BUY"

#             elif prev.ema_fast > prev.ema_slow and curr.ema_fast < curr.ema_slow:
#                 signal = "SELL"

#             if not signal:
#                 continue

#             # 5️⃣ Store signal (no duplicates)
#             conn.execute(
#                 text("""
#                     INSERT INTO strategy_signals
#                     (instrument_token, strategy_name, signal, price, candle_time)
#                     VALUES (:token, :strategy, :signal, :price, :candle_time)
#                     ON CONFLICT (instrument_token, strategy_name, candle_time)
#                     DO NOTHING
#                 """),
#                 {
#                     "token": token,
#                     "strategy": STRATEGY_NAME,
#                     "signal": signal,
#                     "price": curr.close,
#                     "candle_time": curr.candle_time,
#                 }
#             )

#             log.info(
#                 "📈 SIGNAL | %s | token=%s | price=%s | time=%s",
#                 signal, token, curr.close, curr.candle_time
#             )

#     log.info("✅ EMA Strategy Runner completed")


# # -----------------------------
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     run_ema_strategy()




# import logging
# import pandas as pd
# from sqlalchemy import text
# from app.db import engine

# log = logging.getLogger("strategy_runner")

# EMA_FAST = 9
# EMA_SLOW = 21
# STRATEGY = "EMA_CROSS"


# def run_strategy():
#     log.info("🚀 Strategy Runner Started")

#     with engine.connect() as conn:
#         tokens = conn.execute(
#             text("""
#                 SELECT DISTINCT instrument_token
#                 FROM zerodha_candles_1m
#                 WHERE close > 0
#                 GROUP BY instrument_token
#                 HAVING COUNT(*) >= 21
#                 LIMIT 50
#             """)
#         ).fetchall()

#         for (token,) in tokens:
#             df = pd.read_sql(
#                 text("""
#                     SELECT candle_time, close
#                     FROM zerodha_candles_1m
#                     WHERE instrument_token=:t
#                     ORDER BY candle_time
#                 """),
#                 conn,
#                 params={"t": token}
#             )

#             df["ema_fast"] = df["close"].ewm(span=EMA_FAST).mean()
#             df["ema_slow"] = df["close"].ewm(span=EMA_SLOW).mean()

#             if len(df) < EMA_SLOW:
#                 continue

#             prev = df.iloc[-2]
#             curr = df.iloc[-1]

#             signal = None
#             if prev.ema_fast <= prev.ema_slow and curr.ema_fast > curr.ema_slow:
#                 signal = "BUY"
#             elif prev.ema_fast >= prev.ema_slow and curr.ema_fast < curr.ema_slow:
#                 signal = "SELL"

#             if signal:
#                 conn.execute(
#                     text("""
#                         INSERT INTO strategy_signals
#                         (instrument_token, strategy_name, signal, price, candle_time)
#                         VALUES (:t, :s, :sig, :p, :ct)
#                         ON CONFLICT DO NOTHING
#                     """),
#                     {
#                         "t": token,
#                         "s": STRATEGY,
#                         "sig": signal,
#                         "p": curr.close,
#                         "ct": curr.candle_time
#                     }
#                 )
#                 log.info("📈 Signal %s | token=%s", signal, token)

#     log.info("✅ Strategy Runner Completed")


# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     run_strategy()




# strategy_runner.py

import time
import logging
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from app.db import engine

# =====================================================
# CONFIG
# =====================================================
EMA_FAST = 9
EMA_SLOW = 21
STRATEGY = "EMA_CROSS"
CANDLE_SECONDS = 60        # 1 min candle
MAX_TOKENS = 50

# =====================================================
# LOGGER
# =====================================================
log = logging.getLogger("strategy_runner")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =====================================================
# MARKET HOURS (OPTIONAL BUT RECOMMENDED)
# =====================================================
def is_market_open():
    now = datetime.now().time()
    return now >= datetime.strptime("09:15", "%H:%M").time() and \
           now <= datetime.strptime("15:30", "%H:%M").time()

# =====================================================
# STRATEGY LOGIC (ONE RUN)
# =====================================================
def run_strategy_once():
    with engine.connect() as conn:

        tokens = conn.execute(
            text("""
                SELECT instrument_token
                FROM zerodha_candles_1m
                GROUP BY instrument_token
                HAVING COUNT(*) >= :min_candles
                ORDER BY instrument_token
                LIMIT :limit
            """),
            {
                "min_candles": EMA_SLOW + 2,
                "limit": MAX_TOKENS
            }
        ).fetchall()

        for (token,) in tokens:

            df = pd.read_sql(
                text("""
                    SELECT candle_time, close
                    FROM zerodha_candles_1m
                    WHERE instrument_token = :token
                    ORDER BY candle_time
                """),
                conn,
                params={"token": token}
            )

            if len(df) < EMA_SLOW:
                continue

            df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
            df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            signal = None

            if prev.ema_fast <= prev.ema_slow and curr.ema_fast > curr.ema_slow:
                signal = "BUY"

            elif prev.ema_fast >= prev.ema_slow and curr.ema_fast < curr.ema_slow:
                signal = "SELL"

            if not signal:
                continue

            # ---- INSERT SIGNAL (DEDUP SAFE) ----
            conn.execute(
                text("""
                    INSERT INTO strategy_signals (
                        instrument_token,
                        strategy_name,
                        signal,
                        price,
                        candle_time,
                        processed,
                        created_at
                    )
                    VALUES (
                        :token,
                        :strategy,
                        :signal,
                        :price,
                        :candle_time,
                        false,
                        now()
                    )
                    ON CONFLICT DO NOTHING
                """),
                {
                    "token": token,
                    "strategy": STRATEGY,
                    "signal": signal,
                    "price": float(curr.close),
                    "candle_time": curr.candle_time
                }
            )

            log.info("📈 %s signal | token=%s | price=%s",
                     signal, token, curr.close)

# =====================================================
# CONTINUOUS RUNNER
# =====================================================
def run_strategy_loop():
    log.info("🚀 Strategy Runner Started (CONTINUOUS | 1m Candle)")

    while True:
        try:
            if not is_market_open():
                log.info("⏳ Market closed, sleeping...")
                time.sleep(60)
                continue

            start = time.time()
            run_strategy_once()

            elapsed = time.time() - start
            sleep_time = max(0, CANDLE_SECONDS - elapsed)

            log.info("⏱ Cycle done | sleeping %.2f sec", sleep_time)
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            log.warning("🛑 Strategy Runner stopped manually")
            break

        except Exception:
            log.exception("🔥 Strategy Runner crashed, retrying in 5 sec")
            time.sleep(5)

# =====================================================
# ENTRY
# =====================================================
if __name__ == "__main__":
    run_strategy_loop()

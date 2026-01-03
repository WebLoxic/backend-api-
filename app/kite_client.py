

# # app/kite_client.py
# import logging
# from typing import Optional, Dict, Any, List

# from kiteconnect import KiteConnect
# from sqlalchemy import text

# from app.config import KITE_API_KEY, KITE_API_SECRET
# from app.db import SessionLocal

# log = logging.getLogger(__name__)


# class KiteClient:
#     """
#     PRODUCTION-GRADE KITE CLIENT
#     ----------------------------------------
#     ✔ Instruments = GLOBAL (one time)
#     ✔ Tokens = USER scoped
#     ✔ No shared access_token
#     ✔ Multi-user & concurrency safe
#     ✔ Enterprise ready
#     """

#     def __init__(self):
#         if not KITE_API_KEY:
#             raise RuntimeError("KITE_API_KEY not configured")

#     # =====================================================
#     # INTERNAL: CREATE KITE OBJECT
#     # =====================================================
#     def _kite(self, access_token: Optional[str] = None) -> KiteConnect:
#         kite = KiteConnect(api_key=KITE_API_KEY)
#         if access_token:
#             kite.set_access_token(access_token)
#         return kite

#     # =====================================================
#     # USER TOKEN HANDLING
#     # =====================================================
#     def generate_and_store_token(
#         self,
#         request_token: str,
#         user_id: int,
#         user_email: str,
#     ) -> Dict[str, Any]:

#         kite = self._kite()

#         session = kite.generate_session(
#             request_token=request_token,
#             api_secret=KITE_API_SECRET,
#         )

#         access_token = session.get("access_token")
#         public_token = session.get("public_token")

#         if not access_token:
#             raise RuntimeError("access_token missing from Zerodha")

#         db = SessionLocal()
#         try:
#             db.execute(
#                 text("""
#                     INSERT INTO zerodha_broker_token
#                         (user_id, user_email, access_token, public_token, login_time)
#                     VALUES
#                         (:uid, :email, :access, :public, now())
#                     ON CONFLICT (user_id)
#                     DO UPDATE SET
#                         access_token = EXCLUDED.access_token,
#                         public_token = EXCLUDED.public_token,
#                         login_time = now()
#                 """),
#                 {
#                     "uid": user_id,
#                     "email": user_email,
#                     "access": access_token,
#                     "public": public_token,
#                 },
#             )
#             db.commit()

#             log.info("Zerodha token stored | user_id=%s", user_id)

#         finally:
#             db.close()

#         return session

#     def get_user_kite(self, user_id: int) -> KiteConnect:
#         """
#         Returns KiteConnect instance with user's token
#         """
#         db = SessionLocal()
#         try:
#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     WHERE user_id=:uid
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """),
#                 {"uid": user_id},
#             ).fetchone()

#             if not row:
#                 raise RuntimeError("User not connected to Zerodha")

#             return self._kite(row.access_token)

#         finally:
#             db.close()

#     # =====================================================
#     # GLOBAL INSTRUMENT LOADER (ONE TIME)
#     # =====================================================
#     def load_and_store_instruments(self) -> int:
#         """
#         Load Zerodha instruments ONCE using ANY valid access token
#         """

#         db = SessionLocal()
#         try:
#             existing = db.execute(
#                 text("SELECT COUNT(*) FROM zerodha_broker_instrument")
#             ).scalar()

#             if existing and existing > 0:
#                 log.info("Zerodha instruments already loaded | count=%s", existing)
#                 return existing

#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """)
#             ).fetchone()

#             if not row:
#                 raise RuntimeError(
#                     "No Zerodha access token found. Login once before loading instruments."
#                 )

#             kite = self._kite(row.access_token)

#         finally:
#             db.close()

#         log.warning("Loading Zerodha instruments (ONE TIME)")

#         instruments = kite.instruments()
#         if not instruments:
#             raise RuntimeError("Zerodha instruments API returned empty list")

#         db = SessionLocal()
#         try:
#             rows = [
#                 {
#                     "instrument_token": i["instrument_token"],
#                     "exchange": i["exchange"],
#                     "tradingsymbol": i["tradingsymbol"],
#                     "name": i.get("name"),
#                     "segment": i.get("segment"),
#                     "instrument_type": i.get("instrument_type"),
#                 }
#                 for i in instruments
#             ]

#             db.execute(
#                 text("""
#                     INSERT INTO zerodha_broker_instrument
#                         (instrument_token, exchange, tradingsymbol, name, segment, instrument_type)
#                     VALUES
#                         (:instrument_token, :exchange, :tradingsymbol, :name, :segment, :instrument_type)
#                     ON CONFLICT (instrument_token) DO NOTHING
#                 """),
#                 rows,
#             )
#             db.commit()

#             log.info("Zerodha instruments loaded successfully | count=%s", len(rows))
#             return len(rows)

#         finally:
#             db.close()

#     # =====================================================
#     # FAST LOOKUP
#     # =====================================================
#     def get_instrument_token(self, symbol: str) -> int:
#         db = SessionLocal()
#         try:
#             row = db.execute(
#                 text("""
#                     SELECT instrument_token
#                     FROM zerodha_broker_instrument
#                     WHERE tradingsymbol=:s
#                     LIMIT 1
#                 """),
#                 {"s": symbol.upper()},
#             ).fetchone()

#             if not row:
#                 raise ValueError(f"Instrument not found: {symbol}")

#             return int(row.instrument_token)

#         finally:
#             db.close()


# # =====================================================
# # SINGLETON
# # =====================================================
# kite_client = KiteClient()
















# # app/kite_client.py

# import logging
# from typing import Optional, Dict, Any, List
# from kiteconnect import KiteConnect
# from sqlalchemy import text
# from app.config import KITE_API_KEY, KITE_API_SECRET
# from app.db import SessionLocal

# log = logging.getLogger(__name__)


# class KiteClient:
#     """
#     Zerodha Kite Client
#     -------------------
#     ✔ User-scoped tokens
#     ✔ Global instruments (FULL MARKET)
#     ✔ Neon-safe batch inserts
#     ✔ Background-task friendly
#     """

#     def __init__(self):
#         if not KITE_API_KEY or not KITE_API_SECRET:
#             raise RuntimeError("Zerodha API key/secret missing")

#     # -------------------------------------------------
#     # Internal helper
#     # -------------------------------------------------
#     def _kite(self, access_token: Optional[str] = None) -> KiteConnect:
#         kite = KiteConnect(api_key=KITE_API_KEY)
#         if access_token:
#             kite.set_access_token(access_token)
#         return kite

#     # -------------------------------------------------
#     # USER TOKEN HANDLING
#     # -------------------------------------------------
#     def generate_and_store_token(
#         self, request_token: str, user_id: int, user_email: str
#     ) -> Dict[str, Any]:

#         kite = self._kite()
#         session = kite.generate_session(
#             request_token=request_token,
#             api_secret=KITE_API_SECRET,
#         )

#         access_token = session.get("access_token")
#         public_token = session.get("public_token")

#         if not access_token:
#             raise RuntimeError("Zerodha did not return access_token")

#         db = SessionLocal()
#         try:
#             db.execute(
#                 text("""
#                     INSERT INTO zerodha_broker_token
#                         (user_id, user_email, access_token, public_token, login_time)
#                     VALUES
#                         (:uid, :email, :access, :public, now())
#                     ON CONFLICT (user_id)
#                     DO UPDATE SET
#                         access_token = EXCLUDED.access_token,
#                         public_token = EXCLUDED.public_token,
#                         login_time = now()
#                 """),
#                 {
#                     "uid": user_id,
#                     "email": user_email,
#                     "access": access_token,
#                     "public": public_token,
#                 },
#             )
#             db.commit()
#             log.info("Zerodha token stored | user_id=%s", user_id)
#         finally:
#             db.close()

#         return session

#     def get_user_kite(self, user_id: int) -> KiteConnect:
#         db = SessionLocal()
#         try:
#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     WHERE user_id=:uid
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """),
#                 {"uid": user_id},
#             ).fetchone()

#             if not row:
#                 raise RuntimeError("User not connected to Zerodha")

#             return self._kite(row.access_token)
#         finally:
#             db.close()

#     # -------------------------------------------------
#     # GLOBAL INSTRUMENT LOADER (FULL MARKET)
#     # -------------------------------------------------
#     def load_and_store_instruments(self, force_reload: bool = False) -> int:
#         """
#         Load FULL Zerodha market instruments.
#         Covers:
#         - NSE / BSE EQ
#         - NSE F&O
#         - CDS (Currency)
#         - MCX (Commodity)
#         """

#         db = SessionLocal()
#         try:
#             existing = db.execute(
#             text("SELECT COUNT(*) FROM zerodha_broker_instrument")
#                ).scalar()

#             log.info("Existing Zerodha instruments in DB | count=%s", existing)


#             if force_reload:
#                 log.warning("Force reload enabled → clearing instrument table")
#                 db.execute(text("TRUNCATE TABLE zerodha_broker_instrument"))
#                 db.commit()

#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """)
#             ).fetchone()

#             if not row:
#                 raise RuntimeError("No Zerodha token found")

#             kite = self._kite(row.access_token)
#         finally:
#             db.close()

#         log.warning("Loading Zerodha instruments (FULL MARKET)")

#         instruments = kite.instruments()

#         if not isinstance(instruments, list):
#             raise RuntimeError(f"Unexpected instruments type: {type(instruments)}")

#         # 🔍 LOG SEGMENTS (CONFIRM FULL MARKET)
#         segments = sorted({i.get("segment") for i in instruments})
#         log.info("Zerodha segments received: %s", segments)

#         rows: List[Dict[str, Any]] = [
#             {
#                 "instrument_token": i["instrument_token"],
#                 "exchange": i["exchange"],
#                 "tradingsymbol": i["tradingsymbol"],
#                 "name": i.get("name"),
#                 "segment": i.get("segment"),
#                 "instrument_type": i.get("instrument_type"),
#             }
#             for i in instruments
#         ]

#         BATCH_SIZE = 300
#         inserted = 0

#         db = SessionLocal()
#         try:
#             for i in range(0, len(rows), BATCH_SIZE):
#                 chunk = rows[i:i + BATCH_SIZE]
#                 db.execute(
#                     text("""
#                         INSERT INTO zerodha_broker_instrument
#                         (instrument_token, exchange, tradingsymbol, name, segment, instrument_type)
#                         VALUES
#                         (:instrument_token, :exchange, :tradingsymbol, :name, :segment, :instrument_type)
#                         ON CONFLICT (instrument_token) DO NOTHING
#                     """),
#                     chunk,
#                 )
#                 db.commit()
#                 inserted += len(chunk)

#                 if inserted % 3000 == 0:
#                     log.info("Inserted %s instruments so far...", inserted)

#             log.info("Zerodha instruments loaded successfully | total=%s", inserted)
#             return inserted
#         finally:
#             db.close()


# # -------------------------------------------------
# # SINGLETON
# # -------------------------------------------------
# kite_client = KiteClient()







# # app/kite_client.py

# import logging
# from typing import Optional, Dict, Any, List
# from kiteconnect import KiteConnect
# from sqlalchemy import text
# from sqlalchemy.exc import OperationalError

# from app.config import KITE_API_KEY, KITE_API_SECRET
# from app.db import SessionLocal

# log = logging.getLogger(__name__)


# class KiteClient:
#     def __init__(self):
#         if not KITE_API_KEY or not KITE_API_SECRET:
#             raise RuntimeError("Zerodha API key / secret missing")

#     # -------------------------------------------------
#     # INTERNAL KITE INSTANCE
#     # -------------------------------------------------
#     def _kite(self, access_token: Optional[str] = None) -> KiteConnect:
#         kite = KiteConnect(api_key=KITE_API_KEY)
#         if access_token:
#             kite.set_access_token(access_token)
#         return kite

#     # -------------------------------------------------
#     # TOKEN GENERATION & STORAGE
#     # -------------------------------------------------
#     def generate_and_store_token(
#         self, request_token: str, user_id: int, user_email: str
#     ) -> Dict[str, Any]:

#         kite = self._kite()
#         session = kite.generate_session(
#             request_token=request_token,
#             api_secret=KITE_API_SECRET,
#         )

#         access_token = session.get("access_token")
#         public_token = session.get("public_token")

#         if not access_token:
#             raise RuntimeError("Zerodha did not return access_token")

#         db = SessionLocal()
#         try:
#             db.execute(
#                 text("""
#                     INSERT INTO zerodha_broker_token
#                     (user_id, user_email, access_token, public_token, login_time)
#                     VALUES (:uid, :email, :access, :public, now())
#                     ON CONFLICT (user_id)
#                     DO UPDATE SET
#                         access_token = EXCLUDED.access_token,
#                         public_token = EXCLUDED.public_token,
#                         login_time = now()
#                 """),
#                 {
#                     "uid": user_id,
#                     "email": user_email,
#                     "access": access_token,
#                     "public": public_token,
#                 },
#             )
#             db.commit()
#             log.info("Zerodha token stored | user_id=%s", user_id)
#         finally:
#             db.close()

#         return session

#     # -------------------------------------------------
#     # GET USER KITE INSTANCE
#     # -------------------------------------------------
#     def get_user_kite(self, user_id: int) -> KiteConnect:
#         db = SessionLocal()
#         try:
#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     WHERE user_id=:uid
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """),
#                 {"uid": user_id},
#             ).fetchone()

#             if not row:
#                 raise RuntimeError("User not connected to Zerodha")

#             return self._kite(row.access_token)
#         finally:
#             db.close()

#     # -------------------------------------------------
#     # 🔥 FULL MARKET INSTRUMENT LOADER (NEON SAFE)
#     # -------------------------------------------------
#     def load_and_store_instruments(self, force_reload: bool = False) -> int:
#         """
#         Loads FULL Zerodha market instruments:
#         - NSE / BSE EQ
#         - F&O
#         - CDS
#         - MCX
#         """

#         # ---------- DB PRECHECK ----------
#         db = SessionLocal()
#         try:
#             existing = db.execute(
#                 text("SELECT COUNT(*) FROM zerodha_broker_instrument")
#             ).scalar()
#             log.info("Existing Zerodha instruments in DB | count=%s", existing)

#             if force_reload:
#                 log.warning("Force reload enabled → truncating table")
#                 db.execute(text("TRUNCATE TABLE zerodha_broker_instrument RESTART IDENTITY"))
#                 db.commit()

#             row = db.execute(
#                 text("""
#                     SELECT access_token
#                     FROM zerodha_broker_token
#                     ORDER BY login_time DESC
#                     LIMIT 1
#                 """)
#             ).fetchone()

#             if not row:
#                 raise RuntimeError("No Zerodha token found")
#         finally:
#             db.close()

#         # ---------- FETCH FROM ZERODHA ----------
#         kite = self._kite(row.access_token)
#         log.warning("Loading Zerodha instruments (FULL MARKET)")

#         instruments = kite.instruments()
#         if not isinstance(instruments, list):
#             raise RuntimeError("Unexpected instruments response")

#         segments = sorted({i.get("segment") for i in instruments})
#         log.info("Zerodha segments received: %s", segments)

#         rows: List[Dict[str, Any]] = [
#             {
#                 "instrument_token": i["instrument_token"],
#                 "exchange": i["exchange"],
#                 "tradingsymbol": i["tradingsymbol"],
#                 "name": i.get("name"),
#                 "segment": i.get("segment"),
#                 "instrument_type": i.get("instrument_type"),
#             }
#             for i in instruments
#         ]

#         # ---------- INSERT IN BATCHES ----------
#         BATCH_SIZE = 300
#         total_inserted = 0

#         db = SessionLocal()
#         try:
#             for idx in range(0, len(rows), BATCH_SIZE):
#                 chunk = rows[idx: idx + BATCH_SIZE]

#                 try:
#                     result = db.execute(
#                         text("""
#                             INSERT INTO public.zerodha_broker_instrument
#                             (instrument_token, exchange, tradingsymbol, name, segment, instrument_type)
#                             VALUES
#                             (:instrument_token, :exchange, :tradingsymbol, :name, :segment, :instrument_type)
#                             ON CONFLICT (instrument_token) DO NOTHING
#                         """),
#                         chunk,
#                     )
#                     db.commit()

#                     real_inserted = result.rowcount or 0
#                     total_inserted += real_inserted

#                     if total_inserted % 3000 == 0 and real_inserted > 0:
#                         log.info(
#                             "Actually inserted %s new instruments (total=%s)",
#                             real_inserted,
#                             total_inserted,
#                         )

#                 except OperationalError as e:
#                     db.rollback()
#                     log.error("DB connection issue, retrying next batch | %s", e)
#                     continue

#             log.info(
#                 "Zerodha instruments sync completed | new_inserted=%s | api_total=%s",
#                 total_inserted,
#                 len(rows),
#             )
#             return total_inserted

#         finally:
#             db.close()


# # ✅ SINGLETON INSTANCE
# kite_client = KiteClient()





# app/kite_client.py

import logging
from typing import Optional, Dict, Any, List

from kiteconnect import KiteConnect
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import KITE_API_KEY, KITE_API_SECRET
from app.db import SessionLocal

log = logging.getLogger(__name__)


class KiteClient:
    def __init__(self):
        if not KITE_API_KEY or not KITE_API_SECRET:
            raise RuntimeError("Zerodha API key / secret missing")

    # -------------------------------------------------
    # INTERNAL KITE INSTANCE
    # -------------------------------------------------
    def _kite(self, access_token: Optional[str] = None) -> KiteConnect:
        kite = KiteConnect(api_key=KITE_API_KEY)
        if access_token:
            kite.set_access_token(access_token)
        return kite

    # -------------------------------------------------
    # LATEST TOKEN (FOR CRON / TMP SNAPSHOT)
    # -------------------------------------------------
    def _kite_latest(self) -> KiteConnect:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT access_token
                    FROM zerodha_broker_token
                    ORDER BY login_time DESC
                    LIMIT 1
                """)
            ).fetchone()

            if not row:
                raise RuntimeError("No Zerodha token found")

            return self._kite(row.access_token)
        finally:
            db.close()

    # -------------------------------------------------
    # TOKEN GENERATION & STORAGE
    # -------------------------------------------------
    def generate_and_store_token(
        self, request_token: str, user_id: int, user_email: str
    ) -> Dict[str, Any]:

        kite = self._kite()
        session = kite.generate_session(
            request_token=request_token,
            api_secret=KITE_API_SECRET,
        )

        access_token = session.get("access_token")
        public_token = session.get("public_token")

        if not access_token:
            raise RuntimeError("Zerodha did not return access_token")

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO zerodha_broker_token
                    (user_id, user_email, access_token, public_token, login_time)
                    VALUES (:uid, :email, :access, :public, now())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        public_token = EXCLUDED.public_token,
                        login_time = now()
                """),
                {
                    "uid": user_id,
                    "email": user_email,
                    "access": access_token,
                    "public": public_token,
                },
            )
            db.commit()
            log.info("Zerodha token stored | user_id=%s", user_id)
        finally:
            db.close()

        return session

    # -------------------------------------------------
    # GET USER KITE INSTANCE
    # -------------------------------------------------
    def get_user_kite(self, user_id: int) -> KiteConnect:
        db = SessionLocal()
        try:
            row = db.execute(
                text("""
                    SELECT access_token
                    FROM zerodha_broker_token
                    WHERE user_id=:uid
                    ORDER BY login_time DESC
                    LIMIT 1
                """),
                {"uid": user_id},
            ).fetchone()

            if not row:
                raise RuntimeError("User not connected to Zerodha")

            return self._kite(row.access_token)
        finally:
            db.close()

    # =================================================
    # 🔁 TEMP SNAPSHOT LOADER (CRON SAFE)
    # =================================================
    def load_and_store_instruments_tmp(self) -> int:
        """
        Fetch fresh Zerodha instruments
        Store RAW snapshot into TMP table
        No delete, no overwrite
        """

        kite = self._kite_latest()
        instruments = kite.instruments()

        if not instruments or not isinstance(instruments, list):
            raise RuntimeError("Invalid instrument response from Zerodha")

        rows: List[Dict[str, Any]] = [
            {
                "instrument_token": i["instrument_token"],
                "exchange": i["exchange"],
                "tradingsymbol": i["tradingsymbol"],
                "name": i.get("name"),
                "segment": i.get("segment"),
                "instrument_type": i.get("instrument_type"),
            }
            for i in instruments
        ]

        db = SessionLocal()
        inserted = 0

        try:
            for i in range(0, len(rows), 500):
                chunk = rows[i:i + 500]

                result = db.execute(
                    text("""
                        INSERT INTO zerodha_broker_instrument_tmp
                        (instrument_token, exchange, tradingsymbol, name, segment, instrument_type)
                        VALUES
                        (:instrument_token, :exchange, :tradingsymbol, :name, :segment, :instrument_type)
                        ON CONFLICT (instrument_token) DO NOTHING
                    """),
                    chunk,
                )
                db.commit()
                inserted += result.rowcount or 0

        finally:
            db.close()

        log.info("TMP snapshot stored | new_rows=%s | api_total=%s", inserted, len(rows))
        return inserted

    # -------------------------------------------------
    # 🔥 FULL MARKET LOADER (MANUAL / ONE TIME)
    # -------------------------------------------------
    def load_and_store_instruments(self, force_reload: bool = False) -> int:
        """
        Manual / emergency full loader
        NOT used by cron
        """

        kite = self._kite_latest()
        instruments = kite.instruments()

        rows = [
            {
                "instrument_token": i["instrument_token"],
                "exchange": i["exchange"],
                "tradingsymbol": i["tradingsymbol"],
                "name": i.get("name"),
                "segment": i.get("segment"),
                "instrument_type": i.get("instrument_type"),
            }
            for i in instruments
        ]

        db = SessionLocal()
        inserted = 0

        try:
            for i in range(0, len(rows), 300):
                chunk = rows[i:i + 300]

                try:
                    result = db.execute(
                        text("""
                            INSERT INTO zerodha_broker_instrument
                            (instrument_token, exchange, tradingsymbol, name, segment, instrument_type)
                            VALUES
                            (:instrument_token, :exchange, :tradingsymbol, :name, :segment, :instrument_type)
                            ON CONFLICT (instrument_token) DO NOTHING
                        """),
                        chunk,
                    )
                    db.commit()
                    inserted += result.rowcount or 0

                except OperationalError as e:
                    db.rollback()
                    log.error("DB error, skipping batch | %s", e)
                    continue

        finally:
            db.close()

        log.info("Full instrument load done | inserted=%s", inserted)
        return inserted


# ✅ SINGLETON
kite_client = KiteClient()

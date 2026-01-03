"""
CRON: Zerodha Instrument Sync
--------------------------------
GOLDEN RULE:
- Instrument token = STATIC
- Market = DYNAMIC
- Cron = SYNC ONLY
"""

import logging
from datetime import datetime
from sqlalchemy import text
from app.db import SessionLocal
from app.kite_client import kite_client

log = logging.getLogger("cron.instrument_sync")


def sync_zerodha_instruments():
    start = datetime.utcnow()
    log.info("CRON STARTED | Instrument sync")

    # --------------------------------------------------
    # 1️⃣ Load fresh snapshot into TMP table
    # --------------------------------------------------
    tmp_inserted = kite_client.load_and_store_instruments_tmp()
    log.info("TMP snapshot loaded | new_rows=%s", tmp_inserted)

    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 2️⃣ INSERT NEW instruments into MAIN table
        # --------------------------------------------------
        result = db.execute(
            text("""
                INSERT INTO zerodha_broker_instrument
                (instrument_token, exchange, tradingsymbol, name, segment, instrument_type, is_active)
                SELECT
                    t.instrument_token,
                    t.exchange,
                    t.tradingsymbol,
                    t.name,
                    t.segment,
                    t.instrument_type,
                    TRUE
                FROM zerodha_broker_instrument_tmp t
                LEFT JOIN zerodha_broker_instrument m
                    ON m.instrument_token = t.instrument_token
                WHERE m.instrument_token IS NULL
            """)
        )

        inserted = result.rowcount or 0
        db.commit()

        # --------------------------------------------------
        # 3️⃣ MARK EXPIRED instruments INACTIVE
        # --------------------------------------------------
        result = db.execute(
            text("""
                UPDATE zerodha_broker_instrument
                SET is_active = FALSE
                WHERE instrument_token NOT IN (
                    SELECT instrument_token FROM zerodha_broker_instrument_tmp
                )
                AND is_active = TRUE
            """)
        )

        inactive = result.rowcount or 0
        db.commit()

        # --------------------------------------------------
        # 4️⃣ VALIDATION (SANITY CHECK)
        # --------------------------------------------------
        active_count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM zerodha_broker_instrument
                WHERE is_active = TRUE
            """)
        ).scalar()

        if active_count < 15000:
            raise RuntimeError(
                f"Instrument count too low ({active_count}) — aborting sync"
            )

        log.info(
            "CRON DONE | inserted=%s | inactive=%s | active=%s",
            inserted, inactive, active_count
        )

    finally:
        db.close()

    log.info(
        "CRON FINISHED in %.2f sec",
        (datetime.utcnow() - start).total_seconds()
    )

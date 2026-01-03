from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from app.db import SessionLocal

router = APIRouter(prefix="/instruments", tags=["Instruments"])


@router.get("/search")
def search_instruments(
    q: str = Query(..., min_length=1),
    eq_only: int = Query(0)
):
    db = SessionLocal()
    try:
        sql = """
            SELECT
                instrument_token,
                tradingsymbol,
                name,
                exchange,
                segment,
                instrument_type
            FROM tradable_instruments
            WHERE (tradingsymbol ILIKE :q OR name ILIKE :q)
        """

        # ✅ Toggle filter
        if eq_only == 1:
            sql += " AND exchange='NSE' AND instrument_type='EQ'"

        # ✅ MOST IMPORTANT PART
        sql += """
            ORDER BY
              CASE
                WHEN exchange='NSE' AND instrument_type='EQ' THEN 1
                WHEN instrument_type='FUT' THEN 2
                ELSE 3
              END,
              tradingsymbol
            LIMIT 50
        """

        rows = db.execute(
            text(sql),
            {"q": f"%{q}%"}
        ).fetchall()

        return [dict(r._mapping) for r in rows]

    finally:
        db.close()

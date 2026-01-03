from fastapi import APIRouter
from sqlalchemy import text
from app.db import SessionLocal

router = APIRouter(prefix="/api/user", tags=["User Settings"])

@router.post("/trade-mode")
def update_trade_mode(user_id: int, mode: str):
    if mode not in ("AUTO", "MANUAL"):
        return {"error": "Invalid mode"}

    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO user_settings (user_id, trade_mode)
                VALUES (:uid, :mode)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    trade_mode = EXCLUDED.trade_mode,
                    updated_at = now()
            """),
            {"uid": user_id, "mode": mode}
        )
        db.commit()
        return {"ok": True, "mode": mode}
    finally:
        db.close()


from fastapi import APIRouter
from sqlalchemy import text
from app.db import SessionLocal

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.post("/auto-mode")
def set_auto_mode(user_id: int, enabled: bool):
    db = SessionLocal()
    try:
        db.execute(text("""
            INSERT INTO user_trading_settings (user_id, auto_mode)
            VALUES (:uid, :mode)
            ON CONFLICT (user_id)
            DO UPDATE SET auto_mode = :mode, updated_at = now()
        """), {"uid": user_id, "mode": enabled})
        db.commit()
        return {"status": "ok", "auto_mode": enabled}
    finally:
        db.close()

        
@router.post("/strategy-toggle")
def toggle_strategy(user_id: int, strategy: str, enabled: bool):
    db = SessionLocal()
    try:
        db.execute(text("""
            INSERT INTO user_strategy_settings (user_id, strategy_name, enabled)
            VALUES (:uid, :s, :e)
            ON CONFLICT (user_id, strategy_name)
            DO UPDATE SET enabled = :e, updated_at = now()
        """), {
            "uid": user_id,
            "s": strategy,
            "e": enabled
        })
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()

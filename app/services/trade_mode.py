from sqlalchemy import text
from app.db import SessionLocal

def get_trade_mode(user_id: int) -> str:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT trade_mode FROM user_settings WHERE user_id=:uid"),
            {"uid": user_id}
        ).fetchone()

        return row.trade_mode if row else "AUTO"
    finally:
        db.close()


def is_auto_mode(user_id: int) -> bool:
    return get_trade_mode(user_id) == "AUTO"


def is_manual_mode(user_id: int) -> bool:
    return get_trade_mode(user_id) == "MANUAL"

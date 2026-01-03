# # app/api/strategy_routes.py
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from typing import List
# from app.deps import get_db, get_current_user

# from app.schemas import StrategyCreate, StrategyOut
# from app.services.strategy_service import StrategyService

# router = APIRouter(prefix="/strategies", tags=["strategies"])

# @router.post("/", response_model=StrategyOut)
# def create_strategy(payload: StrategyCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
#     svc = StrategyService(db, user)
#     return svc.create(payload)

# @router.get("/", response_model=List[StrategyOut])
# def list_strategies(db: Session = Depends(get_db), user=Depends(get_current_user)):
#     svc = StrategyService(db, user)
#     return svc.list_all()



from fastapi import APIRouter, Depends
from sqlalchemy import text
from app.db import SessionLocal
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])

@router.get("/signals")
def signals(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT * FROM strategy_signals
            WHERE user_id=:u
            ORDER BY created_at DESC
            LIMIT 50
        """), {"u": user["id"]}).fetchall()
        return [dict(r._mapping) for r in rows]
    finally:
        db.close()

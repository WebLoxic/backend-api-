from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.services.positions import get_positions, get_live_pnl

router = APIRouter(prefix="/api/positions", tags=["Positions"])

@router.get("")
def positions(user=Depends(get_current_user)):
    return get_positions(user["id"])

@router.get("/pnl")
def pnl(user=Depends(get_current_user)):
    return get_live_pnl(user["id"])

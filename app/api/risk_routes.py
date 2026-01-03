from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.services.risk import get_risk_config, get_risk_status

router = APIRouter(prefix="/api/risk", tags=["Risk"])

@router.get("/config")
def config(user=Depends(get_current_user)):
    return get_risk_config(user["id"])

@router.get("/status")
def status(user=Depends(get_current_user)):
    return get_risk_status(user["id"])

# app/api/billing_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user_row
from app.schemas import PlanOut, SubscribeIn
from app.services.billing_service import BillingService

router = APIRouter(
    prefix="/billing",
    tags=["billing"]
)

# -----------------------------
# GET ALL PLANS
# -----------------------------
@router.get("/plans", response_model=list[PlanOut])
def get_plans(db: Session = Depends(get_db)):
    svc = BillingService(db, user=None)
    return svc.list_plans()


# -----------------------------
# SUBSCRIBE TO PLAN
# -----------------------------
@router.post("/subscribe")
def subscribe(
    payload: SubscribeIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_row)
):
    svc = BillingService(db, user)
    return svc.subscribe(payload)

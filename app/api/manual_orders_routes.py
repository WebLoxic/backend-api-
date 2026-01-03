# app/api/manual_orders_routes.py

from fastapi import APIRouter, HTTPException

from app.services.trade_mode import is_manual_mode
from app.order_executor import execute_order

router = APIRouter(
    prefix="/api/orders",
    tags=["Manual Orders"]
)


# =====================================================
# 📌 PLACE MANUAL ORDER
# =====================================================
@router.post("/place")
def place_manual_order(
    user_id: int,
    instrument_token: int,
    side: str,
    quantity: int,
):
    """
    Manual order placement API.
    """

    if side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Invalid side")

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be > 0")

    # 🔐 Check MANUAL MODE
    if not is_manual_mode(user_id):
        raise HTTPException(
            status_code=403,
            detail="Switch to MANUAL mode first"
        )

    # 🚀 Execute order
    execute_order(
        user_id=user_id,
        instrument_token=instrument_token,
        side=side,
        quantity=quantity,
        source="MANUAL",
    )

    return {
        "ok": True,
        "message": "Manual order placed successfully"
    }

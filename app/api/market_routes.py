


from fastapi import APIRouter, HTTPException, Query
from app.services.market_utils import get_prev_day_close

router = APIRouter(tags=["Market"])

# =====================================================
# NOTE:
# Live subscribe / unsubscribe WebSocket ke through hota hai
# Ye endpoints sirf compatibility / debug ke liye hain
# =====================================================

@router.post("/market/subscribe/{token}")
def subscribe(token: int):
    """
    Dummy endpoint.
    Actual subscribe happens via WebSocket (/ws/market/{token})
    """
    return {
        "status": "queued",
        "token": token
    }


@router.post("/market/unsubscribe/{token}")
def unsubscribe(token: int):
    """
    Dummy endpoint.
    Actual unsubscribe happens on WS disconnect
    """
    return {
        "status": "noop",
        "token": token
    }


# =====================================================
# PREVIOUS DAY CLOSE
# Used for % Change calculation (Zerodha style)
# =====================================================
@router.get("/market/prev-close")
def market_prev_close(
    token: int = Query(..., description="Zerodha instrument token")
):
    """
    Returns previous trading day's close price.

    Assumptions:
    - zerodha_candles_1m table has historical data
    - previous trading day's last candle (15:30) exists
    """

    prev_close = get_prev_day_close(token)

    if prev_close is None:
        raise HTTPException(
            status_code=404,
            detail="Previous day close not found"
        )

    return {
        "token": token,
        "prev_close": float(prev_close)
    }

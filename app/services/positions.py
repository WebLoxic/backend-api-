# app/services/positions.py

from typing import Dict, Any

def get_positions(user_id: int) -> Dict[str, Any]:
    return {
        "positions": [],
        "count": 0
    }

def get_live_pnl(user_id: int) -> Dict[str, Any]:
    return {
        "pnl": 0.0,
        "day_pnl": 0.0
    }

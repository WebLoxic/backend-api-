# app/services/risk.py

def get_risk_config(user_id: int):
    return {
        "max_loss": 1000,
        "max_trades": 5
    }

def get_risk_status(user_id: int):
    return {
        "allowed": True,
        "reason": None
    }

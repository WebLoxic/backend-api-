from datetime import datetime, timedelta, timezone
from jose import jwt
import os

# ==================================================
# CONFIG
# ==================================================
SECRET_KEY = os.getenv(
    "JWT_SECRET",
    "algo_trader_super_secret_2025_CHANGE_THIS_IN_PROD"
)
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ==================================================
# ACCESS TOKEN
# ==================================================
def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "user_id": data["user_id"],     # ✅ STANDARD
        "email": data.get("email"),
        "role": data.get("role"),
        "type": "access",               # ✅ IMPORTANT
        "exp": int(expire.timestamp())
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ==================================================
# REFRESH TOKEN
# ==================================================
def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": int(expire.timestamp())
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

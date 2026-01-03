from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import text
from app.db import SessionLocal
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
ALGORITHM = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("uid")
        if not user_id:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Invalid token")

    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, email, is_active FROM users WHERE id=:id"),
            {"id": user_id}
        ).first()

        if not user or not user.is_active:
            raise HTTPException(403, "User inactive")

        return {
            "id": user.id,
            "email": user.email
        }
    finally:
        db.close()

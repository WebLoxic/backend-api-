


# app/api/auth_routes.py
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from fastapi import status

# -------------------------------------------------
# ENV + LOGGING
# -------------------------------------------------
load_dotenv()

log = logging.getLogger("app.auth_routes")
log.setLevel(logging.INFO)

COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "smartfin_token")
JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_change")
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60
RESET_TOKEN_EXPIRE_MIN = 30
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# -------------------------------------------------
# INTERNAL IMPORTS
# -------------------------------------------------
from app import models
from app.db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------------------------------------
# PASSWORD HELPERS
# -------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False

# -------------------------------------------------
# JWT HELPERS
# -------------------------------------------------
def create_access_token(email: str, uid: int):
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=2)

    payload = {
        "sub": email,
        "uid": uid,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str):
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True},
        )
    except ExpiredSignatureError:
        log.error("❌ JWT expired")
        return None
    except JWTError as e:
        log.error("❌ JWT invalid: %s", e)
        return None



# -------------------------------------------------
# USER RESOLVER
# -------------------------------------------------
def get_user_from_payload(payload: dict, db: Session):
    uid = payload.get("uid")
    email = payload.get("sub")

    if hasattr(models, "Credential"):
        if uid:
            cred = db.query(models.Credential).filter(models.Credential.user_id == uid).first()
            if cred:
                return cred.user
        if email:
            cred = db.query(models.Credential).filter(models.Credential.email == email).first()
            if cred:
                return cred.user

    if uid:
        return db.query(models.User).filter(models.User.id == uid).first()
    if email:
        return db.query(models.User).filter(models.User.email == email).first()
    return None

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    token = None

    # 1️⃣ Authorization header
    if authorization:
        log.info("AUTH HEADER RAW = %s", authorization)
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # 2️⃣ Cookie fallback
    if not token:
        token = request.cookies.get(COOKIE_NAME)
        log.info("TOKEN FROM COOKIE = %s", token)

    if not token or token.count(".") != 2:
        log.error("❌ Invalid or missing JWT token")
        return None

    payload = decode_jwt(token)
    log.info("JWT PAYLOAD = %s", payload)

    if not payload:
        return None

    uid = payload.get("uid")
    email = payload.get("sub")

    if not uid and not email:
        return None

    return get_user_from_db_by_sub(uid or email, db)


def get_user_from_db_by_sub(sub, db: Session):
    try:
        # UID preferred
        if isinstance(sub, int) or str(sub).isdigit():
            uid = int(sub)
            if hasattr(models, "Credential"):
                cred = db.query(models.Credential).filter(
                    models.Credential.user_id == uid
                ).first()
                if cred:
                    return cred.user

            return db.query(models.User).filter(models.User.id == uid).first()

        # Email fallback
        email = str(sub).lower()
        if hasattr(models, "Credential"):
            cred = db.query(models.Credential).filter(
                models.Credential.email == email
            ).first()
            if cred:
                return cred.user

        return db.query(models.User).filter(models.User.email == email).first()

    except Exception as e:
        log.exception("get_user_from_db_by_sub failed: %s", e)
        return None


# -------------------------------------------------
# ROUTER
# -------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])

# -------------------------------------------------
# SCHEMAS
# -------------------------------------------------
class LoginPayload(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordPayload(BaseModel):
    email: EmailStr

class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@router.post("/login", status_code=200)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    cred = db.query(models.Credential).filter(
        models.Credential.email == email
    ).first()

    if not cred or not verify_password(payload.password, cred.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(email=email, uid=cred.user_id)

    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "Bearer"
    }


# -------------------------------------------------
# ME
# -------------------------------------------------
@router.get("/me", response_model=UserOut)
def me(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = get_current_user(request, db, authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# -------------------------------------------------
# FORGOT PASSWORD
# -------------------------------------------------
@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordPayload, background: BackgroundTasks, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    cred = db.query(models.Credential).filter(models.Credential.email == email).first()
    if not cred:
        return {"ok": True}

    import secrets
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MIN)

    db.execute(
        text("""
        INSERT INTO password_resets (user_id, token, expires_at, used, created_at)
        VALUES (:uid, :token, :exp, false, now())
        """),
        {"uid": cred.user_id, "token": token, "exp": expires},
    )
    db.commit()

    # email sending intentionally skipped here
    return {"ok": True}

# -------------------------------------------------
# RESET PASSWORD
# -------------------------------------------------
@router.post("/reset-password")
def reset_password(payload: ResetPasswordPayload, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
        SELECT * FROM password_resets
        WHERE token=:t AND used=false AND expires_at > now()
        """),
        {"t": payload.token},
    ).fetchone()

    if not row:
        raise HTTPException(400, "Invalid or expired token")

    cred = db.query(models.Credential).filter(models.Credential.user_id == row.user_id).first()
    cred.hashed_password = hash_password(payload.new_password)

    db.execute(text("UPDATE password_resets SET used=true WHERE id=:id"), {"id": row.id})
    db.commit()

    token = create_access_token(email=cred.email, uid=cred.user_id)
    return {"ok": True, "access_token": token, "token_type": "bearer"}

# -------------------------------------------------
# LOGOUT (frontend only)
# -------------------------------------------------
@router.post("/logout")
def logout():
    return {"ok": True}

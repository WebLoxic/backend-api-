import warnings

warnings.filterwarnings(
    "ignore",
    message="Valid config keys have changed in V2*"
)




# # app/main.py
# import os
# import time
# import uuid
# import random
# import asyncio
# import logging
# from datetime import datetime, timedelta
# from typing import Dict, Any

# from dotenv import load_dotenv
# import uvicorn

# # =====================================================
# # ENV + LOGGING
# # =====================================================
# load_dotenv()

# logging.basicConfig(
#     level=os.getenv("LOG_LEVEL", "INFO").upper(),
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )
# log = logging.getLogger("app.main")

# # =====================================================
# # FASTAPI CORE
# # =====================================================
# from fastapi import (
#     FastAPI, Depends, HTTPException,
#     WebSocket, WebSocketDisconnect
# )
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from starlette.middleware.sessions import SessionMiddleware

# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from pydantic import BaseModel

# from sqlalchemy import text
# from app.db import SessionLocal, init_db

# # =====================================================
# # CREATE APP
# # =====================================================
# app = FastAPI(
#     title="QuantX Algo Trading Backend",
#     version="2.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# # =====================================================
# # MIDDLEWARE
# # =====================================================
# SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this")
# app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# allowed_origins = [
#     FRONTEND_URL,
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
#     "http://localhost:3000",
# ]

# if os.getenv("CORS_ALLOW_ALL", "false").lower() in ("1", "true", "yes"):
#     allowed_origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=allowed_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # =====================================================
# # AUTH / JWT
# # =====================================================
# SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
# ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# def create_access_token(user_id: int, email: str) -> str:
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     payload = {"sub": email, "uid": user_id, "exp": expire}
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# def verify_password(plain: str, hashed: str) -> bool:
#     return pwd_context.verify(plain, hashed)


# def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except JWTError:
#         raise HTTPException(401, "Invalid token")

#     uid = payload.get("uid")
#     if not uid:
#         raise HTTPException(401, "Invalid token")

#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("""
#                 SELECT id,email,full_name,is_active,is_superuser,created_at
#                 FROM users WHERE id=:uid LIMIT 1
#             """),
#             {"uid": uid},
#         ).first()

#         if not row:
#             raise HTTPException(401, "User not found")

#         return dict(row._mapping)
#     finally:
#         db.close()

# # =====================================================
# # TOKEN LOGIN
# # =====================================================
# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# @app.post("/token", response_model=Token)
# def token_login(form: OAuth2PasswordRequestForm = Depends()):
#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("SELECT id,email,hashed_password FROM users WHERE email=:e"),
#             {"e": form.username},
#         ).first()

#         if not row or not verify_password(form.password, row.hashed_password):
#             raise HTTPException(401, "Invalid credentials")

#         token = create_access_token(row.id, row.email)
#         return {"access_token": token, "token_type": "bearer"}
#     finally:
#         db.close()

# # =====================================================
# # 🔥 API ROUTES (AUTO LOADER ONLY)
# # =====================================================
# from app.api import router as api_router

# app.include_router(api_router, prefix="/api")

# # =====================================================
# # SIGNAL BROADCASTER
# # =====================================================
# class SignalBroadcaster:
#     def __init__(self):
#         self.queue = asyncio.Queue()
#         self.latest = None

#     async def push(self, signal: Dict[str, Any]):
#         signal.setdefault("id", str(uuid.uuid4()))
#         signal.setdefault("timestamp", datetime.utcnow().isoformat())
#         self.latest = signal
#         await self.queue.put(signal)

#     async def get(self):
#         return await self.queue.get()


# broadcaster = SignalBroadcaster()

# # =====================================================
# # WEBSOCKETS
# # =====================================================
# @app.websocket("/ws/signals")
# async def ws_signals(ws: WebSocket):
#     await ws.accept()
#     try:
#         while True:
#             sig = await broadcaster.get()
#             await ws.send_json(sig)
#     except WebSocketDisconnect:
#         pass


# @app.websocket("/ws/market")
# async def ws_market(ws: WebSocket):
#     await ws.accept()
#     try:
#         while True:
#             await ws.send_json({
#                 "type": "tick",
#                 "symbol": "RELIANCE",
#                 "ltp": round(random.uniform(2300, 2450), 2),
#                 "timestamp": int(time.time()),
#             })
#             await asyncio.sleep(1)
#     except WebSocketDisconnect:
#         pass

# # =====================================================
# # SYSTEM / DEBUG
# # =====================================================
# @app.get("/__routes")
# def list_all_routes():
#     return [{"path": r.path, "methods": list(getattr(r, "methods", []))}
#             for r in app.router.routes]


# @app.get("/health")
# def health():
#     return {
#         "status": "OK",
#         "trading": "ENABLED",
#         "time": int(time.time()),
#     }

# # =====================================================
# # STARTUP / SHUTDOWN
# # =====================================================
# @app.on_event("startup")
# async def startup():
#     init_db()
#     log.info("✅ QuantX Backend Started")


# @app.on_event("shutdown")
# async def shutdown():
#     log.info("🛑 QuantX Backend Stopped")

# # =====================================================
# # ENTRYPOINT
# # =====================================================
# if __name__ == "__main__":
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=int(os.getenv("PORT", 8000)),
#         reload=True,
#     )




# # app/main.py
# import os
# import time
# import uuid
# import random
# import asyncio
# import logging
# from datetime import datetime, timedelta
# from typing import Dict, Any
# from app.market_broadcaster import MarketBroadcaster
# from dotenv import load_dotenv
# import uvicorn

# # =====================================================
# # ENV + LOGGING
# # =====================================================
# load_dotenv()

# logging.basicConfig(
#     level=os.getenv("LOG_LEVEL", "INFO").upper(),
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )
# log = logging.getLogger("app.main")

# # =====================================================
# # FASTAPI CORE
# # =====================================================
# from fastapi import (
#     FastAPI, Depends, HTTPException,
#     WebSocket, WebSocketDisconnect
# )
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from starlette.middleware.sessions import SessionMiddleware

# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from pydantic import BaseModel

# from sqlalchemy import text
# from app.db import SessionLocal, init_db

# # =====================================================
# # ZERODHA WS IMPORTS (NEW)
# # =====================================================
# from app.market_ws import MarketWebSocket
# from app.subscription_manager import SubscriptionManager
# from app.ws_frontend import ws_handler as market_ws_handler
# from app.kite_client import kite_client

# # =====================================================
# # CREATE APP
# # =====================================================
# app = FastAPI(
#     title="QuantX Algo Trading Backend",
#     version="2.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )

# # =====================================================
# # MIDDLEWARE
# # =====================================================
# SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this")
# app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# allowed_origins = [
#     FRONTEND_URL,
#     "http://localhost:5173",
#     "http://127.0.0.1:5173",
#     "http://localhost:3000",
# ]

# if os.getenv("CORS_ALLOW_ALL", "false").lower() in ("1", "true", "yes"):
#     allowed_origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=allowed_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # =====================================================
# # AUTH / JWT
# # =====================================================
# SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
# ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# def create_access_token(user_id: int, email: str) -> str:
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     payload = {"sub": email, "uid": user_id, "exp": expire}
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# def verify_password(plain: str, hashed: str) -> bool:
#     return pwd_context.verify(plain, hashed)


# def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except JWTError:
#         raise HTTPException(401, "Invalid token")

#     uid = payload.get("uid")
#     if not uid:
#         raise HTTPException(401, "Invalid token")

#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("""
#                 SELECT id,email,full_name,is_active,is_superuser,created_at
#                 FROM users WHERE id=:uid LIMIT 1
#             """),
#             {"uid": uid},
#         ).first()

#         if not row:
#             raise HTTPException(401, "User not found")

#         return dict(row._mapping)
#     finally:
#         db.close()

# # =====================================================
# # TOKEN LOGIN
# # =====================================================
# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# @app.post("/token", response_model=Token)
# def token_login(form: OAuth2PasswordRequestForm = Depends()):
#     db = SessionLocal()
#     try:
#         row = db.execute(
#             text("SELECT id,email,hashed_password FROM users WHERE email=:e"),
#             {"e": form.username},
#         ).first()

#         if not row or not verify_password(form.password, row.hashed_password):
#             raise HTTPException(401, "Invalid credentials")

#         token = create_access_token(row.id, row.email)
#         return {"access_token": token, "token_type": "bearer"}
#     finally:
#         db.close()

# # =====================================================
# # API ROUTES
# # =====================================================
# from app.api import router as api_router
# app.include_router(api_router, prefix="/api")

# # =====================================================
# # SIGNAL BROADCASTER (UNCHANGED)
# # =====================================================
# class SignalBroadcaster:
#     def __init__(self):
#         self.queue = asyncio.Queue()
#         self.latest = None

#     async def push(self, signal: Dict[str, Any]):
#         signal.setdefault("id", str(uuid.uuid4()))
#         signal.setdefault("timestamp", datetime.utcnow().isoformat())
#         self.latest = signal
#         await self.queue.put(signal)

#     async def get(self):
#         return await self.queue.get()


# broadcaster = SignalBroadcaster()

# # =====================================================
# # ZERODHA MARKET WS GLOBALS
# # =====================================================
# market_ws: MarketWebSocket | None = None
# subscription_manager: SubscriptionManager | None = None

# # =====================================================
# # WEBSOCKETS (EXISTING)
# # =====================================================
# @app.websocket("/ws/signals")
# async def ws_signals(ws: WebSocket):
#     await ws.accept()
#     try:
#         while True:
#             sig = await broadcaster.get()
#             await ws.send_json(sig)
#     except WebSocketDisconnect:
#         pass


# @app.websocket("/ws/market")
# async def ws_market_dummy(ws: WebSocket):
#     """Dummy market WS (unchanged)"""
#     await ws.accept()
#     try:
#         while True:
#             await ws.send_json({
#                 "type": "tick",
#                 "symbol": "RELIANCE",
#                 "ltp": round(random.uniform(2300, 2450), 2),
#                 "timestamp": int(time.time()),
#             })
#             await asyncio.sleep(1)
#     except WebSocketDisconnect:
#         pass

# # =====================================================
# # LIVE MARKET WS (ZERODHA)
# # =====================================================
# @app.websocket("/ws/market-live/{user_id}")
# async def ws_market_live(ws: WebSocket, user_id: int):
#     if not subscription_manager:
#         await ws.close(code=1011)
#         return

#     await market_ws_handler(ws, user_id)

# # =====================================================
# # SYSTEM / DEBUG
# # =====================================================
# @app.get("/__routes")
# def list_all_routes():
#     return [{"path": r.path, "methods": list(getattr(r, "methods", []))}
#             for r in app.router.routes]


# @app.get("/health")
# def health():
#     return {
#         "status": "OK",
#         "trading": "ENABLED",
#         "time": int(time.time()),
#     }

# # =====================================================
# # STARTUP / SHUTDOWN
# # =====================================================
# @app.on_event("startup")
# async def startup_core():
#     init_db()
#     log.info("✅ QuantX Backend Core Started")


# @app.on_event("startup")
# async def startup_market_ws():
#     global market_ws, subscription_manager

#     kite = kite_client.get_user_kite(user_id=1)

#     market_ws = MarketWebSocket(
#         api_key=kite.api_key,
#         access_token=kite.access_token,
#     )
#     market_ws.start()

#     subscription_manager = SubscriptionManager(market_ws)
#     log.info("🟢 Zerodha Market WS + SubscriptionManager started")


# @app.on_event("shutdown")
# async def shutdown():
#     log.info("🛑 QuantX Backend Stopped")

# # =====================================================
# # ENTRYPOINT
# # =====================================================
# if __name__ == "__main__":
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=int(os.getenv("PORT", 8000)),
#         reload=True,
#     )




# app/main.py
import os
import time
import uuid
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from dotenv import load_dotenv
import uvicorn

# =====================================================
# ENV + LOGGING
# =====================================================
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("app.main")

# =====================================================
# FASTAPI CORE
# =====================================================
from fastapi import (
    FastAPI, Depends, HTTPException,
    WebSocket, WebSocketDisconnect
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware

from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from sqlalchemy import text
from app.db import SessionLocal, init_db

# =====================================================
# ZERODHA / MARKET IMPORTS
# =====================================================
from app.market_ws import MarketWebSocket
from app.subscription_manager import SubscriptionManager
from app.market_broadcaster import MarketBroadcaster
from app.kite_client import kite_client

# =====================================================
# CREATE APP
# =====================================================
app = FastAPI(
    title="QuantX Algo Trading Backend",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =====================================================
# MIDDLEWARE
# =====================================================
SESSION_SECRET = os.getenv("SESSION_SECRET", "change_this")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

if os.getenv("CORS_ALLOW_ALL", "false").lower() in ("1", "true", "yes"):
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# AUTH / JWT
# =====================================================
SECRET_KEY = os.getenv("JWT_SECRET", "super_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "uid": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_current_user_row(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid token")

    uid = payload.get("uid")
    if not uid:
        raise HTTPException(401, "Invalid token")

    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT id,email,full_name,is_active,is_superuser,created_at
                FROM users WHERE id=:uid LIMIT 1
            """),
            {"uid": uid},
        ).first()

        if not row:
            raise HTTPException(401, "User not found")

        return dict(row._mapping)
    finally:
        db.close()

# =====================================================
# TOKEN LOGIN
# =====================================================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/token", response_model=Token)
def token_login(form: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id,email,hashed_password FROM users WHERE email=:e"),
            {"e": form.username},
        ).first()

        if not row or not verify_password(form.password, row.hashed_password):
            raise HTTPException(401, "Invalid credentials")

        token = create_access_token(row.id, row.email)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

# =====================================================
# API ROUTES
# =====================================================
from app.api import router as api_router
app.include_router(api_router, prefix="/api")

# =====================================================
# SIGNAL BROADCASTER (UNCHANGED)
# =====================================================
class SignalBroadcaster:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.latest = None

    async def push(self, signal: Dict[str, Any]):
        signal.setdefault("id", str(uuid.uuid4()))
        signal.setdefault("timestamp", datetime.utcnow().isoformat())
        self.latest = signal
        await self.queue.put(signal)

    async def get(self):
        return await self.queue.get()


signal_broadcaster = SignalBroadcaster()

# =====================================================
# MARKET WS GLOBAL OBJECTS (IMPORTANT)
# =====================================================
market_ws: Optional[MarketWebSocket] = None
subscription_manager: Optional[SubscriptionManager] = None
market_broadcaster = MarketBroadcaster()

# =====================================================
# WEBSOCKETS
# =====================================================
@app.websocket("/ws/signals")
async def ws_signals(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            sig = await signal_broadcaster.get()
            await ws.send_json(sig)
    except WebSocketDisconnect:
        pass


# 🔹 Dummy market WS (for testing / fallback)
@app.websocket("/ws/market")
async def ws_market_dummy(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({
                "symbol": "RELIANCE",
                "ltp": round(random.uniform(2300, 2450), 2),
                "timestamp": int(time.time()),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


# 🔥 REAL ZERODHA MARKET WS (TOKEN BASED)
@app.websocket("/ws/market/{instrument_token}")
async def ws_market_live(ws: WebSocket, instrument_token: int):
    if not market_ws:
        await ws.close(code=1011)
        return

    await ws.accept()
    await market_broadcaster.connect(instrument_token, ws)
    market_ws.subscribe(instrument_token)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await market_broadcaster.disconnect(instrument_token, ws)
        market_ws.unsubscribe(instrument_token)

# =====================================================
# SYSTEM / DEBUG
# =====================================================
@app.get("/__routes")
def list_all_routes():
    return [{"path": r.path, "methods": list(getattr(r, "methods", []))}
            for r in app.router.routes]


@app.get("/health")
def health():
    return {
        "status": "OK",
        "trading": "ENABLED",
        "time": int(time.time()),
    }

# =====================================================
# STARTUP / SHUTDOWN
# =====================================================
@app.on_event("startup")
async def startup_core():
    init_db()
    log.info("✅ QuantX Backend Core Started")


@app.on_event("startup")
async def startup_market_ws():
    global market_ws, subscription_manager

    kite = kite_client.get_user_kite(user_id=1)

    market_ws = MarketWebSocket(
        api_key=kite.api_key,
        access_token=kite.access_token,
        broadcaster=market_broadcaster
    )
    market_ws.start()

    subscription_manager = SubscriptionManager(market_ws)
    log.info("🟢 Zerodha Market WS + Broadcaster started")


@app.on_event("shutdown")
async def shutdown():
    log.info("🛑 QuantX Backend Stopped")

# =====================================================
# ENTRYPOINT
# =====================================================
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )

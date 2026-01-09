

# app/db.py

import os
import logging
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# =================================================
# LOGGING
# =================================================
log = logging.getLogger("app.db")
log.setLevel(logging.INFO)

if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    log.addHandler(handler)

# =================================================
# ENV LOADING
# =================================================
# 👉 Local development me .env load hoga
# 👉 Render / production me OS env hi use hoga
ENV = os.getenv("ENV", "development")

if ENV != "production":
    load_dotenv()
    log.info("Loaded .env file (development mode)")
else:
    log.info("Production mode detected, skipping load_dotenv()")

# =================================================
# DATABASE URL (ONLY SOURCE OF TRUTH)
# =================================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL not set in environment")

# DEBUG (1–2 deploy ke baad hata dena)
log.info(f"DATABASE_URL USED = {DATABASE_URL}")

# =================================================
# SQLALCHEMY ENGINE (NEON SAFE)
# =================================================
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes"),
    future=True,

    # Neon / Render friendly settings
    pool_pre_ping=True,     # auto-reconnect if SSL drops
    pool_recycle=300,       # recycle every 5 minutes
    pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
)

# =================================================
# SESSION
# =================================================
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)

# =================================================
# BASE
# =================================================
Base = declarative_base()

# =================================================
# INIT DB (called on startup)
# =================================================
def init_db() -> None:
    log.info("Initializing database...")
    import app.models  # noqa: F401  (important: models must be imported)
    Base.metadata.create_all(bind=engine)
    log.info("Database tables created (if not already present).")

# =================================================
# FASTAPI DEPENDENCY
# =================================================
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

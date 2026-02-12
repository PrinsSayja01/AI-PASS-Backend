from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Stable DB location (always the same, no matter where you run the server from)
BASE_DIR = Path(__file__).resolve().parent.parent   # .../python
DB_FILE = BASE_DIR / "aipass.sqlite3"
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # needed for sqlite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

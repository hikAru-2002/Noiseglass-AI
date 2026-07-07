import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Falls back to a local SQLite file for dev when DATABASE_URL isn't set
# (production on Railway always sets DATABASE_URL to Postgres).
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./signal_local.db")

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
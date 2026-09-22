"""SQLAlchemy engine and session management."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine_kwargs: dict = {"pool_pre_ping": True}
# SQLite (used in tests) does not support pool_size/max_overflow.
if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update(pool_size=5, max_overflow=10)
if settings.environment == "development":
    engine_kwargs["echo"] = True

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

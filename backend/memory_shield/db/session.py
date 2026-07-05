"""Async SQLAlchemy session for sprout_app Postgres."""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .models import (  # noqa: F401 — register tables
    AnalyticsMeta,
    AnalyticsVideo,
    Draft,
    Fingerprint,
    OAuthCredentials,
    Preference,
    TelegramPollState,
    User,
    VideoStatsSnapshot,
)

DATABASE_URL = os.getenv("SPROUT_DATABASE_URL", "")
if not DATABASE_URL:
    from pathlib import Path
    _db_path = Path(__file__).resolve().parents[1] / ".cache" / "sprout_app.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{_db_path}"

_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _session_factory = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _engine, _session_factory


async def init_db() -> None:
    engine, _ = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_engine()
    async with factory() as session:
        yield session

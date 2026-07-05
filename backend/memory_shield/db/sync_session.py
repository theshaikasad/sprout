"""Sync SQLAlchemy session for lifecycle/preferences (called from sync code paths)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from .models import (  # noqa: F401
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

SYNC_URL = os.getenv("SPROUT_DATABASE_URL", f"sqlite:///{Path(__file__).resolve().parents[1] / '.cache' / 'sprout_app.db'}")
if SYNC_URL.startswith("sqlite"):
    Path(SYNC_URL.split("///", 1)[-1]).parent.mkdir(parents=True, exist_ok=True)
if "+asyncpg" in SYNC_URL:
    SYNC_URL = SYNC_URL.replace("+asyncpg", "+psycopg2")

_sync_engine = None


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(SYNC_URL, pool_pre_ping=True)
    return _sync_engine


def init_sync_db() -> None:
    SQLModel.metadata.create_all(_get_sync_engine())
    from .schema import ensure_schema
    ensure_schema()


@contextmanager
def sync_session() -> Iterator[Session]:
    with Session(_get_sync_engine()) as session:
        yield session

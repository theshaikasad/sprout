"""Lightweight schema patches for existing sprout_app DBs (no Alembic)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from .sync_session import _get_sync_engine


def _is_postgres(conn) -> bool:
    return conn.dialect.name == "postgresql"


def _add_column(conn, table: str, column: str, sqlite_ddl: str, postgres_ddl: str) -> None:
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if column in cols:
        return
    ddl = postgres_ddl if _is_postgres(conn) else sqlite_ddl
    conn.execute(text(ddl))
    conn.commit()


def ensure_schema() -> None:
    engine = _get_sync_engine()
    with engine.connect() as conn:
        # --- users (multi-user migration columns) ---
        user_cols = [
            (
                "cognee_user_id",
                "ALTER TABLE users ADD COLUMN cognee_user_id TEXT",
                "ALTER TABLE users ADD COLUMN cognee_user_id UUID",
            ),
            (
                "cognee_dataset_id",
                "ALTER TABLE users ADD COLUMN cognee_dataset_id TEXT",
                "ALTER TABLE users ADD COLUMN cognee_dataset_id UUID",
            ),
            (
                "youtube_channel_id",
                "ALTER TABLE users ADD COLUMN youtube_channel_id VARCHAR(64) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN youtube_channel_id VARCHAR(64) DEFAULT ''",
            ),
            (
                "youtube_handle",
                "ALTER TABLE users ADD COLUMN youtube_handle VARCHAR(128) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN youtube_handle VARCHAR(128) DEFAULT ''",
            ),
            (
                "channel_title",
                "ALTER TABLE users ADD COLUMN channel_title VARCHAR(256) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN channel_title VARCHAR(256) DEFAULT ''",
            ),
            (
                "channel_avatar",
                "ALTER TABLE users ADD COLUMN channel_avatar VARCHAR(512) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN channel_avatar VARCHAR(512) DEFAULT ''",
            ),
            (
                "subscriber_count",
                "ALTER TABLE users ADD COLUMN subscriber_count INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN subscriber_count INTEGER DEFAULT 0",
            ),
            (
                "channel_video_count",
                "ALTER TABLE users ADD COLUMN channel_video_count INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN channel_video_count INTEGER DEFAULT 0",
            ),
            (
                "onboarding_status",
                "ALTER TABLE users ADD COLUMN onboarding_status VARCHAR(32) DEFAULT 'pending'",
                "ALTER TABLE users ADD COLUMN onboarding_status VARCHAR(32) DEFAULT 'pending'",
            ),
            (
                "onboarding_stage",
                "ALTER TABLE users ADD COLUMN onboarding_stage VARCHAR(32) DEFAULT 'idle'",
                "ALTER TABLE users ADD COLUMN onboarding_stage VARCHAR(32) DEFAULT 'idle'",
            ),
            (
                "onboarding_detail",
                "ALTER TABLE users ADD COLUMN onboarding_detail VARCHAR(512) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN onboarding_detail VARCHAR(512) DEFAULT ''",
            ),
            (
                "onboarding_error",
                "ALTER TABLE users ADD COLUMN onboarding_error VARCHAR(512) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN onboarding_error VARCHAR(512) DEFAULT ''",
            ),
            (
                "telegram_chat_id",
                "ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(32) DEFAULT ''",
                "ALTER TABLE users ADD COLUMN telegram_chat_id VARCHAR(32) DEFAULT ''",
            ),
            (
                "is_demo",
                "ALTER TABLE users ADD COLUMN is_demo BOOLEAN DEFAULT 0",
                "ALTER TABLE users ADD COLUMN is_demo BOOLEAN DEFAULT FALSE",
            ),
            (
                "holdout_cutoff",
                "ALTER TABLE users ADD COLUMN holdout_cutoff DATE",
                "ALTER TABLE users ADD COLUMN holdout_cutoff DATE",
            ),
        ]
        for col, sqlite_ddl, pg_ddl in user_cols:
            _add_column(conn, "users", col, sqlite_ddl, pg_ddl)

        _add_column(
            conn,
            "preferences",
            "competitor_alerts",
            "ALTER TABLE preferences ADD COLUMN competitor_alerts BOOLEAN DEFAULT 0 NOT NULL",
            "ALTER TABLE preferences ADD COLUMN competitor_alerts BOOLEAN DEFAULT FALSE NOT NULL",
        )

        _add_column(
            conn,
            "preferences",
            "declared_niche",
            "ALTER TABLE preferences ADD COLUMN declared_niche TEXT DEFAULT ''",
            "ALTER TABLE preferences ADD COLUMN declared_niche TEXT DEFAULT ''",
        )

        _add_column(
            conn,
            "drafts",
            "sprouted_video_id",
            "ALTER TABLE drafts ADD COLUMN sprouted_video_id VARCHAR(64) DEFAULT ''",
            "ALTER TABLE drafts ADD COLUMN sprouted_video_id VARCHAR(64) DEFAULT ''",
        )

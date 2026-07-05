"""SQLModel tables for sprout_app — per-user state keyed by Firebase uid."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: str = Field(primary_key=True, max_length=128)
    email: str = Field(default="", max_length=320)
    display_name: str = Field(default="", max_length=256)
    photo_url: str = Field(default="", max_length=512)
    cognee_user_id: Optional[uuid.UUID] = Field(default=None, unique=True)
    cognee_dataset_id: Optional[uuid.UUID] = Field(default=None)
    youtube_channel_id: str = Field(default="", max_length=64, index=True)
    youtube_handle: str = Field(default="", max_length=128)
    channel_title: str = Field(default="", max_length=256)
    channel_avatar: str = Field(default="", max_length=512)
    subscriber_count: int = Field(default=0)
    channel_video_count: int = Field(default=0)
    onboarding_status: str = Field(default="pending", max_length=32)
    onboarding_stage: str = Field(default="idle", max_length=32)
    onboarding_detail: str = Field(default="", max_length=512)
    onboarding_error: str = Field(default="", max_length=512)
    telegram_chat_id: str = Field(default="", max_length=32, index=True)
    is_demo: bool = Field(default=False)
    holdout_cutoff: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthCredentials(SQLModel, table=True):
    __tablename__ = "oauth_credentials"

    uid: str = Field(primary_key=True, foreign_key="users.uid", max_length=128)
    access_token_enc: bytes = Field(default=b"")
    refresh_token_enc: bytes = Field(default=b"")
    expires_at: Optional[datetime] = Field(default=None)
    scopes: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class Preference(SQLModel, table=True):
    __tablename__ = "preferences"

    uid: str = Field(primary_key=True, foreign_key="users.uid", max_length=128)
    goals: str = Field(default="")
    declared_niche: str = Field(default="")
    tone: str = Field(default="encouraging", max_length=64)
    interruption_budget: str = Field(default="normal", max_length=32)
    competitor_alerts: bool = Field(default=False)
    competitor_exclusions: list[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )


class Draft(SQLModel, table=True):
    __tablename__ = "drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    uid: str = Field(foreign_key="users.uid", max_length=128, index=True)
    title: str = Field(default="")
    angle: str = Field(default="")
    format_name: str = Field(default="")
    topic_labels: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    state: str = Field(default="seed", max_length=16, index=True)
    provenance: str = Field(default="")
    derived_from: str = Field(default="")
    concept_art_path: str = Field(default="")
    sprouted_video_id: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    planted_at: Optional[datetime] = Field(default=None)
    sprouted_at: Optional[datetime] = Field(default=None)


class AnalyticsMeta(SQLModel, table=True):
    __tablename__ = "analytics_meta"

    uid: str = Field(primary_key=True, foreign_key="users.uid", max_length=128)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    holdout_cutoff: Optional[date] = Field(default=None)
    baselines: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class AnalyticsVideo(SQLModel, table=True):
    __tablename__ = "analytics_videos"
    __table_args__ = (UniqueConstraint("uid", "video_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(foreign_key="users.uid", max_length=128, index=True)
    video_id: str = Field(max_length=32)
    title: str = Field(default="")
    published: str = Field(default="")
    is_short: bool = Field(default=False)
    format: str = Field(default="")
    topics: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    hook_style: str = Field(default="")
    views: int = Field(default=0)
    impressions: int = Field(default=0)
    ctr: float = Field(default=0.0)
    avg_view_percentage: float = Field(default=0.0)
    subs_gained: int = Field(default=0)
    watch_hours: float = Field(default=0.0)
    growth_score: float = Field(default=0.0)
    ratio_vs_baseline: float = Field(default=0.0)
    content_multiplier: float = Field(default=1.0)
    retention_curve: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    traffic_sources: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )


class VideoStatsSnapshot(SQLModel, table=True):
    __tablename__ = "video_stats_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(foreign_key="users.uid", max_length=128, index=True)
    video_id: str = Field(max_length=32)
    views: int = Field(default=0)
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    captured_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Fingerprint(SQLModel, table=True):
    __tablename__ = "fingerprints"

    uid: str = Field(primary_key=True, foreign_key="users.uid", max_length=128)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class TelegramPollState(SQLModel, table=True):
    __tablename__ = "telegram_poll_state"

    id: int = Field(default=1, primary_key=True)
    offset: int = Field(default=0)

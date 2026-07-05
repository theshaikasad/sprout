"""Per-user onboarding pipeline — scoped ingest, never global wipe."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from cognee.modules.users.methods import create_user

from .analytics_fixture import build_analytics
from .analytics_youtube import build_analytics_real
from .analyzer import run_pattern_scan, write_patterns_to_graph
from .auth.tokens import decrypt
from .auth.youtube_oauth import access_token_from_row
from .cognee_context import user_cognee_context
from .config import HOLDOUT_CUTOFF
from .corpus import build_corpus
from .db.context import UserContext, set_current_user
from .db.models import OAuthCredentials, User
from .db.sync_session import sync_session
from .fingerprint import build_fingerprint
from .ingest import main as run_ingest


def _set_status(uid: str, stage: str, detail: str = "", error: str = "") -> None:
    with sync_session() as session:
        u = session.get(User, uid)
        if u:
            u.onboarding_stage = stage
            u.onboarding_detail = detail
            u.onboarding_error = error[:512] if error else ""
            u.onboarding_status = "error" if stage == "error" else (
                "ready" if stage == "done" else "building"
            )
            u.updated_at = datetime.utcnow()
            session.add(u)
            session.commit()


async def ensure_cognee_user(uid: str, email: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Create Cognee user + dataset ids if missing."""
    from cognee.infrastructure.databases.relational import create_db_and_tables

    await create_db_and_tables()
    with sync_session() as session:
        u = session.get(User, uid)
        if u and u.cognee_user_id and u.cognee_dataset_id:
            return u.cognee_user_id, u.cognee_dataset_id

    cognee_user = await create_user(
        email=email or f"{uid}@example.com",
        password=str(uuid.uuid4()),
        is_verified=True,
    )
    from cognee.modules.data.methods import create_dataset

    dataset = await create_dataset(f"sprout_{uid}", cognee_user)
    dataset_id = dataset.id
    with sync_session() as session:
        u = session.get(User, uid)
        if u:
            u.cognee_user_id = cognee_user.id
            u.cognee_dataset_id = dataset_id
            u.holdout_cutoff = HOLDOUT_CUTOFF
            session.add(u)
            session.commit()
    return cognee_user.id, dataset_id


async def run_onboarding(uid: str, email: str = "", use_real_analytics: bool = True) -> None:
    try:
        cognee_uid, dataset_id = await ensure_cognee_user(uid, email)
        with sync_session() as session:
            user = session.get(User, uid)
        set_current_user(
            UserContext(
                uid=uid,
                is_demo=bool(user and user.is_demo),
                cognee_user_id=cognee_uid,
                cognee_dataset_id=dataset_id,
                youtube_channel_id=user.youtube_channel_id if user else "",
                telegram_chat_id=user.telegram_chat_id if user else "",
            )
        )
        ctx_dataset = dataset_id
        ctx_user = cognee_uid

        async with user_cognee_context(
            dataset_id=ctx_dataset, user_id=ctx_user
        ):
            _set_status(uid, "fetching", "building corpus")
            with sync_session() as session:
                user = session.get(User, uid)
            handle = None
            if user and user.youtube_handle:
                handle = user.youtube_handle
                if not handle.startswith("@"):
                    handle = f"@{handle}"
            corpus = await asyncio.to_thread(build_corpus, handle, _progress_cb(uid))

            _set_status(uid, "analytics", "pulling analytics")
            if use_real_analytics and uid != "demo":
                with sync_session() as session:
                    creds = session.get(OAuthCredentials, uid)
                    user = session.get(User, uid)
                if creds and user and user.youtube_channel_id:
                    token = access_token_from_row(
                        creds.access_token_enc,
                        creds.refresh_token_enc,
                        creds.expires_at,
                    )
                    await asyncio.to_thread(
                        build_analytics_real,
                        token,
                        user.youtube_channel_id,
                        corpus,
                        uid,
                    )
                else:
                    await asyncio.to_thread(build_analytics, corpus)
            else:
                await asyncio.to_thread(build_analytics, corpus)

            _set_status(uid, "ingesting", "building knowledge graph")
            await run_ingest(fresh=True, skip_lane_b=False)

            _set_status(uid, "patterns", "running pattern analyzer")
            patterns = await asyncio.to_thread(run_pattern_scan, corpus["live"])
            await write_patterns_to_graph(patterns, corpus["live"])

            await asyncio.to_thread(build_fingerprint, corpus)
            _set_status(uid, "done", "memory built")
    except Exception as e:
        _set_status(uid, "error", str(e)[:200], str(e))


def _progress_cb(uid: str):
    def cb(stage: str, detail: str = ""):
        _set_status(uid, stage, detail)
    return cb


def get_onboarding_status(uid: str) -> dict:
    with sync_session() as session:
        u = session.get(User, uid)
        if not u:
            return {"stage": "idle", "detail": "", "status": "pending", "error": ""}
        return {
            "stage": u.onboarding_stage,
            "detail": u.onboarding_detail,
            "status": u.onboarding_status,
            "error": u.onboarding_error,
            "channel": {
                "title": u.channel_title,
                "avatar": u.channel_avatar,
                "subscribers": u.subscriber_count,
                "handle": u.youtube_handle,
            } if u.channel_title else None,
        }

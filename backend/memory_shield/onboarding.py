"""Per-user onboarding pipeline — scoped ingest, never global wipe."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime

from cognee.modules.users.methods import create_user

from .analytics_fixture import build_analytics
from .analytics_youtube import build_analytics_real
from .analyzer import run_pattern_scan, write_patterns_to_graph
from .auth.tokens import decrypt
from .auth.youtube_oauth import access_token_from_row
from .cognee_context import user_cognee_context
from .cold_start import classify_tier, filter_patterns, needs_declared_niche, TIER_ESTABLISHED
from .config import HOLDOUT_CUTOFF
from .corpus import build_corpus
from .db.context import UserContext, set_current_user
from .db.models import OAuthCredentials, User
from .db.sync_session import sync_session
from .fingerprint import build_fingerprint
from .ingest import main as run_ingest
from .preferences import get_preferences


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
    from fastapi_users.exceptions import UserAlreadyExists
    from cognee.modules.users.methods.get_user_by_email import get_user_by_email

    await create_db_and_tables()
    with sync_session() as session:
        u = session.get(User, uid)
        if u and u.cognee_user_id and u.cognee_dataset_id:
            return u.cognee_user_id, u.cognee_dataset_id

    try:
        cognee_user = await create_user(
            email=email or f"{uid}@example.com",
            password=str(uuid.uuid4()),
            is_verified=True,
        )
    except UserAlreadyExists:
        cognee_user = await get_user_by_email(email)
        if not cognee_user:
            raise

    from cognee.modules.data.methods.create_dataset import create_dataset

    # Check if dataset already exists for this user
    from cognee.modules.data.methods.get_datasets_by_name import get_datasets_by_name
    try:
        datasets = await get_datasets_by_name(f"sprout_{uid}", cognee_user)
        dataset = datasets[0] if datasets else None
    except Exception:
        dataset = None
    if not dataset:
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

        prefs = get_preferences(uid)
        declared_niche = prefs.get("declared_niche", "")

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

            live_count = len(corpus["live"])
            tier = classify_tier(live_count)

            with sync_session() as session:
                u = session.get(User, uid)
                if u:
                    u.channel_video_count = live_count
                    session.add(u)
                    session.commit()

            if needs_declared_niche(tier, declared_niche):
                _set_status(
                    uid,
                    "error",
                    "Tell Sprout what your channel is about before building memory.",
                    "declared_niche_required",
                )
                return

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
            # Cloud Run cannot reach OpenAI embeddings API — skip Lane B in prod.
            prod_mode = bool(os.getenv("SPROUT_DATABASE_URL", ""))
            skip_lane_b = prod_mode
            if skip_lane_b:
                print("onboarding ingest: prod mode — skipping Lane B (no embeddings available)", flush=True)
            lane_b_ok = True
            try:
                await run_ingest(fresh=True, skip_lane_b=skip_lane_b)
                lane_b_ok = not skip_lane_b
            except RecursionError as e:
                print(f"onboarding ingest: RecursionError — {e}, attempting skip-lane-b fallback", flush=True)
                try:
                    await run_ingest(fresh=False, skip_lane_b=True)
                    lane_b_ok = False
                except Exception as e2:
                    print(f"onboarding ingest: fallback also failed — {e2}", flush=True)
                    raise
            except Exception as e:
                msg = str(e)
                print(f"onboarding ingest: failed — {msg}", flush=True)
                if "embedding" in msg.lower() or "timeout" in msg.lower() or "422" in msg:
                    print("onboarding ingest: retrying with Lane A only (skip embeddings)", flush=True)
                    try:
                        await run_ingest(fresh=False, skip_lane_b=True)
                        lane_b_ok = False
                    except Exception as e2:
                        print(f"onboarding ingest: Lane-A-only fallback failed — {e2}", flush=True)
                        raise
                else:
                    raise

            patterns = await asyncio.to_thread(run_pattern_scan, corpus["live"])
            patterns = filter_patterns(patterns, tier)
            if patterns:
                _set_status(uid, "patterns", "running pattern analyzer")
                await write_patterns_to_graph(patterns, corpus["live"])
            elif tier != TIER_ESTABLISHED:
                _set_status(uid, "patterns", "skipping patterns — catalog still warming up")

            await asyncio.to_thread(
                build_fingerprint,
                corpus,
                declared_niche=declared_niche,
                tier=tier,
                uid=uid,
            )
            _set_status(uid, "done", "memory built")
    except Exception as e:
        _set_status(uid, "error", str(e)[:200], str(e))


def _progress_cb(uid: str):
    def cb(stage: str, detail: str = ""):
        _set_status(uid, stage, detail)
    return cb


def get_onboarding_status(uid: str) -> dict:
    from .cold_start import TIER_ESTABLISHED
    from .fingerprint import load_fingerprint

    with sync_session() as session:
        u = session.get(User, uid)
        if not u:
            return {"stage": "idle", "detail": "", "status": "pending", "error": ""}
        prefs = get_preferences(uid)
        channel_video_count = u.channel_video_count
        declared_niche = prefs.get("declared_niche", "")
        preview_tier = classify_tier(channel_video_count)

        cold_start = None
        genre = None
        if u.onboarding_status == "ready":
            try:
                fp = load_fingerprint(uid)
                cold_start = fp.get("cold_start")
                genre = fp.get("genre")
            except Exception:
                pass

        return {
            "stage": u.onboarding_stage,
            "detail": u.onboarding_detail,
            "status": u.onboarding_status,
            "error": u.onboarding_error,
            "channel_video_count": channel_video_count,
            "preview_tier": preview_tier,
            "needs_niche": needs_declared_niche(preview_tier, declared_niche),
            "declared_niche": declared_niche,
            "cold_start": cold_start,
            "genre": genre,
            "use_backtest_reveal": (
                cold_start is None or cold_start.get("tier") == TIER_ESTABLISHED
            ),
            "channel": {
                "title": u.channel_title,
                "avatar": u.channel_avatar,
                "subscribers": u.subscriber_count,
                "handle": u.youtube_handle,
                "video_count": channel_video_count,
            } if u.channel_title else None,
        }

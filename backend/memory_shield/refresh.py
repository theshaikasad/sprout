"""Background refresh — per-user analytics, patterns, live stats."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from sqlmodel import select

from .analytics_fixture import build_analytics
from .analytics_youtube import build_analytics_real
from .analyzer import run_pattern_scan, write_patterns_to_graph
from .auth.tokens import decrypt
from .auth.youtube_oauth import access_token_from_row
from .cognee_context import user_cognee_context
from .cold_start import classify_tier, filter_patterns
from .config import CREATOR_HANDLE, DIGEST_PATH
from .corpus import build_corpus, load_corpus
from .db.context import UserContext, set_current_user
from .db.models import OAuthCredentials, User
from .db.sync_session import sync_session
from .fingerprint import build_fingerprint
from .preferences import get_preferences
from .lifecycle import compost_stale_seeds
from .live_stats import poll_live_stats
from .nudges import maybe_send_proactive_nudges
from .track import get_track


async def run_refresh_for_user(
    user: User,
    *,
    rebuild_corpus: bool = False,
) -> dict:
    """Refresh one user's memory caches and graph patterns."""
    ctx = UserContext(
        uid=user.uid,
        is_demo=user.is_demo,
        cognee_user_id=user.cognee_user_id,
        cognee_dataset_id=user.cognee_dataset_id,
        youtube_channel_id=user.youtube_channel_id,
        telegram_chat_id=user.telegram_chat_id,
    )
    set_current_user(ctx)

    handle = user.youtube_handle or CREATOR_HANDLE
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"

    nudges_sent: list[str] = []

    async with user_cognee_context(ctx=ctx):
        if rebuild_corpus and handle:
            await asyncio.to_thread(build_corpus, handle)
        corpus = load_corpus()

        if user.is_demo or not user.youtube_channel_id:
            await asyncio.to_thread(build_analytics, corpus)
        else:
            with sync_session() as session:
                creds = session.get(OAuthCredentials, user.uid)
            if creds:
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
                    user.uid,
                )
            else:
                await asyncio.to_thread(build_analytics, corpus)

        patterns = await asyncio.to_thread(run_pattern_scan, corpus["live"])
        live_count = len(corpus["live"])
        tier = classify_tier(live_count)
        patterns = filter_patterns(patterns, tier)
        if patterns:
            await write_patterns_to_graph(patterns, corpus["live"])

        prefs = get_preferences(user.uid)
        fp = await asyncio.to_thread(
            build_fingerprint,
            corpus,
            declared_niche=prefs.get("declared_niche", ""),
            tier=tier,
            uid=user.uid,
        )

        with sync_session() as session:
            u = session.get(User, user.uid)
            if u:
                u.channel_video_count = live_count
                session.add(u)
                session.commit()
        composted = compost_stale_seeds()
        track = await get_track(force=True)
        await asyncio.to_thread(poll_live_stats, user.uid)

        if user.telegram_chat_id:
            try:
                nudges_sent = await maybe_send_proactive_nudges(user)
            except Exception as e:
                print(f"proactive nudges skipped for {user.uid}: {e}")

    digest = {
        "uid": user.uid,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "patterns_found": len(patterns),
        "seeds_composted": len(composted),
        "track_headline": track.get("headline"),
        "genre": fp.get("genre", {}).get("label"),
        "nudges_sent": len(nudges_sent),
    }
    return digest


async def run_refresh(rebuild_corpus: bool = False) -> list[dict]:
    with sync_session() as session:
        users = list(
            session.exec(
                select(User).where(User.onboarding_status == "ready")
            ).all()
        )

    digests: list[dict] = []
    for user in users:
        try:
            digests.append(await run_refresh_for_user(user, rebuild_corpus=rebuild_corpus))
        except Exception as e:
            digests.append({"uid": user.uid, "error": str(e)[:200]})

    if digests and len(users) == 1 and users[0].uid == "demo":
        DIGEST_PATH.write_text(json.dumps(digests[0], ensure_ascii=False, indent=1))
    return digests


if __name__ == "__main__":
    result = asyncio.run(run_refresh())
    print(json.dumps(result, indent=2))

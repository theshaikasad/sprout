"""Per-user Cognee dataset context wrapper."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from cognee.context_global_variables import set_database_global_context_variables

from .db.context import UserContext, get_current_user, set_current_user


def is_postgres_multi_user() -> bool:
    from .config import SPROUT_DATABASE_URL

    return bool(SPROUT_DATABASE_URL and "postgres" in SPROUT_DATABASE_URL)


async def ensure_cognee_ids(ctx: UserContext) -> UserContext:
    """Ensure sprout_app.users row has cognee_user_id + cognee_dataset_id (Postgres only)."""
    if not is_postgres_multi_user():
        return ctx
    if ctx.cognee_user_id and ctx.cognee_dataset_id:
        return ctx

    from .db.models import User
    from .db.sync_session import sync_session
    from .onboarding import ensure_cognee_user

    email = "demo@sprout.internal" if ctx.uid == "demo" else f"{ctx.uid}@sprout.internal"
    await ensure_cognee_user(ctx.uid, email)

    with sync_session() as session:
        user = session.get(User, ctx.uid)
        if not user:
            return ctx
        updated = UserContext(
            uid=user.uid,
            is_demo=user.is_demo,
            cognee_user_id=user.cognee_user_id,
            cognee_dataset_id=user.cognee_dataset_id,
            youtube_channel_id=user.youtube_channel_id or "",
            telegram_chat_id=user.telegram_chat_id or "",
        )
    set_current_user(updated)
    return updated


@asynccontextmanager
async def with_user_cognee(
    ctx: Optional[UserContext] = None,
    dataset_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
) -> AsyncIterator[UserContext]:
    """Scope all Cognee ops to the authenticated user's dataset."""
    ctx = ctx or get_current_user()
    if not is_postgres_multi_user():
        yield ctx
        return

    ctx = await ensure_cognee_ids(ctx)
    ds = dataset_id or ctx.cognee_dataset_id
    uid = user_id or ctx.cognee_user_id
    if ds is None or uid is None:
        raise RuntimeError(
            f"Cognee dataset not provisioned for uid={ctx.uid!r} — run onboarding first"
        )
    async with set_database_global_context_variables(ds, uid):
        yield ctx


# Backward-compatible alias used by onboarding + refresh
user_cognee_context = with_user_cognee

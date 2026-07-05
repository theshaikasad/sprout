"""FastAPI auth dependencies."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.context import UserContext, set_current_user
from ..db.repos import count_real_users, get_or_create_demo_user, get_user, upsert_user
from ..db.session import get_session
from .firebase import firebase_configured, verify_id_token


async def bind_request_user(authorization: str | None = None) -> UserContext:
    """Set user context from Authorization header (middleware + tests)."""
    from ..db.sync_session import sync_session, init_sync_db
    from ..db.models import User, Preference
    from ..db.repos import count_real_users_sync

    try:
        init_sync_db()
    except Exception:
        pass

    if not authorization or not authorization.startswith("Bearer "):
        with sync_session() as session:
            from sqlmodel import select
            user = session.get(User, "demo")
            if not user:
                user = User(
                    uid="demo",
                    display_name="Demo Creator",
                    is_demo=True,
                    onboarding_status="ready",
                )
                session.add(user)
                session.flush()
                session.add(Preference(uid="demo"))
                session.commit()
                session.refresh(user)
            ctx = UserContext(
                uid=user.uid,
                is_demo=user.is_demo,
                cognee_user_id=user.cognee_user_id,
                cognee_dataset_id=user.cognee_dataset_id,
                youtube_channel_id=user.youtube_channel_id,
                telegram_chat_id=user.telegram_chat_id,
            )
            set_current_user(ctx)
            return ctx

    if not firebase_configured():
        raise HTTPException(503, "Firebase not configured")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = verify_id_token(token)
    except Exception:
        raise HTTPException(401, "invalid Firebase token")

    uid = decoded["uid"]
    with sync_session() as session:
        user = session.get(User, uid)
        if user is None:
            if count_real_users_sync(session) >= 10:
                raise HTTPException(403, "Sprout is full — 10 creators max for now")
            user = User(
                uid=uid,
                email=decoded.get("email", ""),
                display_name=decoded.get("name", ""),
                photo_url=decoded.get("picture", ""),
            )
            session.add(user)
            session.flush()
            session.add(Preference(uid=uid))
            session.commit()
            session.refresh(user)

        ctx = UserContext(
            uid=user.uid,
            is_demo=user.is_demo,
            cognee_user_id=user.cognee_user_id,
            cognee_dataset_id=user.cognee_dataset_id,
            youtube_channel_id=user.youtube_channel_id,
            telegram_chat_id=user.telegram_chat_id,
        )
        set_current_user(ctx)
        return ctx


async def optional_user(
    authorization: Annotated[Optional[str], Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> UserContext:
    """Demo mode when no Firebase token — uses shared demo user."""
    if not authorization or not authorization.startswith("Bearer "):
        user = await get_or_create_demo_user(session)
        ctx = UserContext(
            uid=user.uid,
            is_demo=user.is_demo,
            cognee_user_id=user.cognee_user_id,
            cognee_dataset_id=user.cognee_dataset_id,
            youtube_channel_id=user.youtube_channel_id,
            telegram_chat_id=user.telegram_chat_id,
        )
        set_current_user(ctx)
        return ctx

    if not firebase_configured():
        raise HTTPException(503, "Firebase not configured")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = verify_id_token(token)
    except Exception:
        raise HTTPException(401, "invalid Firebase token")

    uid = decoded["uid"]
    user = await get_user(session, uid)
    if user is None:
        if await count_real_users(session) >= 10:
            raise HTTPException(403, "Sprout is full — 10 creators max for now")
        user = await upsert_user(
            session,
            uid=uid,
            email=decoded.get("email", ""),
            display_name=decoded.get("name", ""),
            photo_url=decoded.get("picture", ""),
        )

    ctx = UserContext(
        uid=user.uid,
        is_demo=user.is_demo,
        cognee_user_id=user.cognee_user_id,
        cognee_dataset_id=user.cognee_dataset_id,
        youtube_channel_id=user.youtube_channel_id,
        telegram_chat_id=user.telegram_chat_id,
    )
    set_current_user(ctx)
    return ctx


async def current_user(ctx: UserContext = Depends(optional_user)) -> UserContext:
    return ctx


async def require_firebase_user(ctx: UserContext = Depends(optional_user)) -> UserContext:
    if ctx.uid == "demo" and not ctx.is_demo:
        raise HTTPException(401, "sign in required")
    if ctx.uid == "demo":
        raise HTTPException(401, "sign in required")
    return ctx

"""User + state persistence in sprout_app Postgres."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import OAuthCredentials, Preference, User


MAX_USERS = 10


def count_real_users_sync(session) -> int:
    from sqlmodel import select
    r = session.exec(select(func.count()).select_from(User).where(User.is_demo == False))  # noqa: E712
    return int(r.one())


async def count_real_users(session: AsyncSession) -> int:
    r = await session.execute(
        select(func.count()).select_from(User).where(User.is_demo == False)  # noqa: E712
    )
    return int(r.scalar_one())


async def get_user(session: AsyncSession, uid: str) -> Optional[User]:
    r = await session.execute(select(User).where(User.uid == uid))
    return r.scalar_one_or_none()


async def upsert_user(session: AsyncSession, **fields) -> User:
    uid = fields["uid"]
    user = await get_user(session, uid)
    if user is None:
        user = User(**fields)
        session.add(user)
    else:
        for k, v in fields.items():
            setattr(user, k, v)
        user.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_demo_user(session: AsyncSession) -> User:
    user = await get_user(session, "demo")
    if user:
        return user
    user = User(
        uid="demo",
        display_name="Demo Creator",
        is_demo=True,
        onboarding_status="ready",
    )
    session.add(user)
    prefs = Preference(uid="demo")
    session.add(prefs)
    await session.commit()
    await session.refresh(user)
    return user


async def save_oauth_tokens(
    session: AsyncSession,
    uid: str,
    access_enc: bytes,
    refresh_enc: bytes,
    expires_at: datetime | None,
    scopes: list[str],
) -> None:
    row = await session.get(OAuthCredentials, uid)
    if row is None:
        row = OAuthCredentials(uid=uid)
        session.add(row)
    row.access_token_enc = access_enc
    row.refresh_token_enc = refresh_enc
    row.expires_at = expires_at
    row.scopes = scopes
    await session.commit()


async def get_oauth_credentials(session: AsyncSession, uid: str) -> Optional[OAuthCredentials]:
    return await session.get(OAuthCredentials, uid)


async def get_user_by_telegram_chat(session: AsyncSession, chat_id: str) -> Optional[User]:
    r = await session.execute(select(User).where(User.telegram_chat_id == chat_id))
    return r.scalar_one_or_none()

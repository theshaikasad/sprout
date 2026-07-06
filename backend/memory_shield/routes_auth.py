"""Auth + onboarding routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.deps import current_user, require_firebase_user
from .auth.youtube_oauth import (
    auth_url,
    exchange_code,
    get_channel_info,
    oauth_configured,
    tokens_to_encrypted,
)
from .config import FRONTEND_URL, TELEGRAM_BOT_TOKEN
from .db.context import UserContext
from .db.models import User
from .db.repos import save_oauth_tokens, upsert_user
from .db.session import get_session
from .niche import save_declared_niche
from .onboarding import get_onboarding_status, run_onboarding
from .telegram_bot import get_bot_username, make_link_token

router = APIRouter()


class NicheBody(BaseModel):
    niche: str


@router.get("/auth/youtube/url")
async def youtube_auth_url(ctx: UserContext = Depends(require_firebase_user)):
    if not oauth_configured():
        raise HTTPException(503, "Google OAuth not configured")
    return {"url": auth_url(state=ctx.uid)}


@router.get("/auth/youtube/callback")
async def youtube_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    session: AsyncSession = Depends(get_session),
):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/signup?oauth_error={error}")
    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/signup?oauth_error=missing_code")
    try:
        tokens = exchange_code(code)
        access_token = tokens.get("access_token", "")
        channel = get_channel_info(access_token)
        access_enc, refresh_enc, expires = tokens_to_encrypted(tokens)
        await save_oauth_tokens(
            session, state, access_enc, refresh_enc, expires,
            scopes=["youtube.readonly", "yt-analytics.readonly"],
        )
        await upsert_user(
            session,
            uid=state,
            youtube_channel_id=channel["channel_id"],
            youtube_handle=channel.get("handle", ""),
            channel_title=channel["title"],
            channel_avatar=channel.get("avatar", ""),
            subscriber_count=channel.get("subscribers", 0),
            channel_video_count=channel.get("video_count", 0),
        )
        return RedirectResponse(
            f"{FRONTEND_URL}/signup?oauth_channel={channel['title']}"
            f"&video_count={channel.get('video_count', 0)}"
        )
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/signup?oauth_error={str(e)[:200]}")


@router.post("/onboarding/niche")
async def onboarding_niche(
    body: NicheBody,
    ctx: UserContext = Depends(require_firebase_user),
):
    niche = body.niche.strip()
    if not niche:
        raise HTTPException(400, "niche is required")
    prefs = save_declared_niche(niche, ctx.uid)
    return {"ok": True, "declared_niche": prefs.get("declared_niche", "")}


@router.post("/onboarding/start")
async def onboarding_start(
    ctx: UserContext = Depends(require_firebase_user),
    session: AsyncSession = Depends(get_session),
):
    status = get_onboarding_status(ctx.uid)
    if status.get("status") == "building":
        raise HTTPException(409, "onboarding already in progress")
    if status.get("status") == "ready":
        return {"ok": True, "status": "ready"}
    if status.get("needs_niche"):
        raise HTTPException(400, "declare your channel niche before building memory")
    user = await session.get(User, ctx.uid)
    email = user.email if user else ""
    asyncio.create_task(run_onboarding(ctx.uid, email, use_real_analytics=not ctx.is_demo))
    return {"ok": True, "status": "building"}


@router.get("/onboarding/status")
async def onboarding_status(ctx: UserContext = Depends(current_user)):
    return get_onboarding_status(ctx.uid)


@router.get("/telegram/link")
async def telegram_link(ctx: UserContext = Depends(current_user)):
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(503, "Telegram bot not configured")
    token = make_link_token(ctx.uid)
    bot = get_bot_username()
    if not bot:
        raise HTTPException(503, "Could not resolve Telegram bot username — set TELEGRAM_BOT_USERNAME")
    start = f"link_{token}"
    return {
        "url": f"https://t.me/{bot}?start={start}",
        "start_command": f"/start {start}",
        "token": token,
        "bot_username": bot,
    }


@router.get("/telegram/status")
async def telegram_status(ctx: UserContext = Depends(current_user)):
    from .telegram_bot import chat_id_for_uid

    chat_id = chat_id_for_uid(ctx.uid)
    masked = ""
    if chat_id:
        masked = f"…{chat_id[-4:]}" if len(chat_id) > 4 else chat_id
    return {"linked": bool(chat_id), "chat_id_masked": masked}

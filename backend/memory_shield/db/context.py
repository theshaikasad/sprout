"""Per-request user context — set by auth dependency, read by state modules."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserContext:
    uid: str
    is_demo: bool = False
    cognee_user_id: Optional[uuid.UUID] = None
    cognee_dataset_id: Optional[uuid.UUID] = None
    youtube_channel_id: str = ""
    telegram_chat_id: str = ""


_current_user: ContextVar[Optional[UserContext]] = ContextVar("current_user", default=None)


def set_current_user(ctx: UserContext | None) -> None:
    _current_user.set(ctx)


def get_current_user() -> UserContext:
    ctx = _current_user.get()
    if ctx is None:
        # Legacy demo path — single-tenant local dev without auth
        return UserContext(uid="demo", is_demo=True)
    return ctx


def require_uid() -> str:
    return get_current_user().uid

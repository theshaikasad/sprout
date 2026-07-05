"""Per-user Cognee dataset context wrapper."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from cognee.context_global_variables import set_database_global_context_variables

from .db.context import UserContext, get_current_user


@asynccontextmanager
async def user_cognee_context(
    ctx: Optional[UserContext] = None,
    dataset_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
) -> AsyncIterator[None]:
    """Scope all Cognee ops to the authenticated user's dataset."""
    ctx = ctx or get_current_user()
    ds = dataset_id or ctx.cognee_dataset_id
    uid = user_id or ctx.cognee_user_id
    if ds is None or uid is None:
        yield
        return
    async with set_database_global_context_variables(ds, uid):
        yield

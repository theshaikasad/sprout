"""User memory: goals, tone, competitor exclusions, interruption budget."""

from __future__ import annotations

import uuid

from sqlmodel import select

from .cognee_env import cognee  # noqa: F401
from cognee.low_level import setup
from cognee.tasks.storage import add_data_points

from .db.context import require_uid
from .db.models import Preference
from .db.sync_session import sync_session
from .graph_models import Preference as PreferenceNode

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "memory-shield-preferences")


def _id(key: str, value: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"{key}|{value}")


def _default_prefs() -> dict:
    return {
        "competitor_exclusions": [],
        "competitor_alerts": False,
        "interruption_budget": "normal",
        "goals": "",
        "declared_niche": "",
        "tone": "encouraging",
    }


def get_preferences(uid: str | None = None) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        p = session.get(Preference, uid)
        if not p:
            return _default_prefs()
        return {
            "competitor_exclusions": p.competitor_exclusions or [],
            "competitor_alerts": bool(getattr(p, "competitor_alerts", False)),
            "interruption_budget": p.interruption_budget,
            "goals": p.goals,
            "declared_niche": p.declared_niche or "",
            "tone": p.tone,
        }


async def set_preference(key: str, value: str, uid: str | None = None) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        p = session.get(Preference, uid)
        if not p:
            p = Preference(uid=uid)
            session.add(p)
        if key == "competitor_exclusions":
            excl = set(p.competitor_exclusions or [])
            excl.add(value)
            p.competitor_exclusions = sorted(excl)
        elif key == "competitor_alerts":
            p.competitor_alerts = str(value).lower() in ("1", "true", "yes", "on")
        else:
            setattr(p, key, value)
        session.add(p)
        session.commit()

    await setup()
    from .cognee_context import with_user_cognee

    async with with_user_cognee():
        await add_data_points(
            [PreferenceNode(id=_id(key, value), key=key, value=value, belongs_to_set=["my_channel"])],
            embed_triplets=False,
        )
    return get_preferences(uid)


async def remove_competitor_exclusion(handle: str, uid: str | None = None) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        p = session.get(Preference, uid)
        if not p:
            return _default_prefs()
        p.competitor_exclusions = [h for h in (p.competitor_exclusions or []) if h != handle]
        session.add(p)
        session.commit()
    return get_preferences(uid)

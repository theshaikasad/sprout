"""Set declared niche for cold-start onboarding (0-video channels)."""

from __future__ import annotations

from .db.context import require_uid
from .db.models import Preference
from .db.sync_session import sync_session


def save_declared_niche(niche: str, uid: str | None = None) -> dict:
    uid = uid or require_uid()
    niche = niche.strip()[:512]
    with sync_session() as session:
        p = session.get(Preference, uid)
        if not p:
            p = Preference(uid=uid)
            session.add(p)
        p.declared_niche = niche
        session.add(p)
        session.commit()
    from .preferences import get_preferences

    return get_preferences(uid)

"""Postgres-backed draft lifecycle (uid-scoped)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import select

from .config import SEED_COMPOST_DAYS
from .db.context import require_uid
from .db.models import Draft
from .db.sync_session import sync_session


def _now() -> datetime:
    return datetime.utcnow()


def _draft_to_dict(d: Draft) -> dict:
    return {
        "id": str(d.id),
        "title": d.title,
        "angle": d.angle,
        "format_name": d.format_name,
        "topic_labels": d.topic_labels or [],
        "state": d.state,
        "provenance": d.provenance,
        "derived_from": d.derived_from,
        "concept_art_path": d.concept_art_path,
        "created_at": d.created_at.isoformat() + "Z" if d.created_at else "",
        "updated_at": d.updated_at.isoformat() + "Z" if d.updated_at else "",
        "planted_at": d.planted_at.isoformat() + "Z" if d.planted_at else "",
        "sprouted_at": d.sprouted_at.isoformat() + "Z" if d.sprouted_at else "",
        "posted_video_id": d.sprouted_video_id,
    }


def list_drafts(state: str | None = None, uid: str | None = None) -> list[dict]:
    uid = uid or require_uid()
    with sync_session() as session:
        q = select(Draft).where(Draft.uid == uid)
        if state:
            q = q.where(Draft.state == state)
        rows = session.exec(q).all()
    drafts = [_draft_to_dict(d) for d in rows]
    return sorted(drafts, key=lambda d: d.get("updated_at", ""), reverse=True)


def list_seeds(uid: str | None = None) -> list[dict]:
    return list_drafts("seed", uid)


def list_planted(uid: str | None = None) -> list[dict]:
    return list_drafts("planted", uid)


def list_sprouted(uid: str | None = None) -> list[dict]:
    return list_drafts("sprouted", uid)


def _similar(existing: Draft, title: str, angle: str = "") -> bool:
    t = title.lower().strip()
    if existing.title.lower().strip() == t:
        return True
    if angle and existing.angle.lower().strip() == angle.lower().strip():
        return True
    return False


def save_idea(
    title: str,
    angle: str = "",
    format_name: str = "",
    topic_labels: list[str] | None = None,
    state: str = "seed",
    provenance: str = "",
    derived_from: str = "",
    uid: str | None = None,
) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        rows = session.exec(
            select(Draft).where(Draft.uid == uid).where(
                (Draft.state == "seed") | (Draft.state == "planted")
            )
        ).all()
        for d in rows:
            if _similar(d, title, angle):
                d.title = title
                d.angle = angle or d.angle
                d.format_name = format_name or d.format_name
                d.topic_labels = topic_labels or d.topic_labels
                if state != "seed":
                    d.state = state
                d.updated_at = _now()
                d.provenance = provenance or d.provenance
                if state == "planted" and not d.planted_at:
                    d.planted_at = _now()
                session.add(d)
                session.commit()
                session.refresh(d)
                return _draft_to_dict(d)

        d = Draft(
            uid=uid,
            title=title,
            angle=angle,
            format_name=format_name,
            topic_labels=topic_labels or [],
            state=state,
            provenance=provenance,
            derived_from=derived_from,
            planted_at=_now() if state == "planted" else None,
        )
        session.add(d)
        session.commit()
        session.refresh(d)
        return _draft_to_dict(d)


def plant_idea(draft_id: str, uid: str | None = None) -> dict:
    from .concept_art import concept_art_url

    uid = uid or require_uid()
    with sync_session() as session:
        d = session.get(Draft, uuid.UUID(draft_id))
        if not d or d.uid != uid:
            raise ValueError(f"unknown draft {draft_id!r}")
        d.state = "planted"
        d.planted_at = _now()
        d.updated_at = _now()
        d.concept_art_path = concept_art_url(draft_id, d.title)
        session.add(d)
        session.commit()
        session.refresh(d)
        return _draft_to_dict(d)


async def mark_sprouted(draft_id: str, video_id: str = "", uid: str | None = None) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        d = session.get(Draft, uuid.UUID(draft_id))
        if not d or d.uid != uid:
            raise ValueError(f"unknown draft {draft_id!r}")
        d.state = "sprouted"
        d.sprouted_at = _now()
        d.updated_at = _now()
        d.sprouted_video_id = video_id
        session.add(d)
        session.commit()
        session.refresh(d)
        out = _draft_to_dict(d)

    try:
        from cognee.infrastructure.databases.graph import get_graph_engine
        from .kg import Graph

        g = await Graph.load()
        wanted_topics = {t.lower() for t in out.get("topic_labels", [])}
        wanted_format = (out.get("format_name") or "").lower()
        node_ids = [
            nid for nid, p in g.props.items()
            if (p.get("type") == "Topic" and (p.get("label") or "").lower() in wanted_topics)
            or (p.get("type") == "Format" and wanted_format and (p.get("name") or "").lower() == wanted_format)
        ]
        if node_ids:
            engine = await get_graph_engine()
            current = await engine.get_node_feedback_weights(node_ids) or {}
            new_weights = {nid: min(5.0, float(current.get(nid) or 0.0) + 0.3) for nid in node_ids}
            await engine.set_node_feedback_weights(new_weights)
    except Exception as e:
        print(f"lifecycle: sprout reweight skipped — {e}")

    return out


def update_draft(draft_id: str, patch: dict, uid: str | None = None) -> dict:
    uid = uid or require_uid()
    with sync_session() as session:
        d = session.get(Draft, uuid.UUID(draft_id))
        if not d or d.uid != uid:
            raise ValueError(f"unknown draft {draft_id!r}")
        for k, v in patch.items():
            if k != "id" and hasattr(d, k):
                setattr(d, k, v)
        d.updated_at = _now()
        session.add(d)
        session.commit()
        session.refresh(d)
        return _draft_to_dict(d)


def delete_draft(draft_id: str, uid: str | None = None) -> None:
    uid = uid or require_uid()
    with sync_session() as session:
        d = session.get(Draft, uuid.UUID(draft_id))
        if d and d.uid == uid:
            session.delete(d)
            session.commit()


def compost_stale_seeds(uid: str | None = None) -> list[str]:
    uid = uid or require_uid()
    cutoff = date.today() - timedelta(days=SEED_COMPOST_DAYS)
    composted = []
    with sync_session() as session:
        rows = session.exec(select(Draft).where(Draft.uid == uid, Draft.state == "seed")).all()
        for d in rows:
            if d.created_at and d.created_at.date() < cutoff:
                composted.append(str(d.id))
                session.delete(d)
        session.commit()
    return composted


def capture_seed_from_turn(user_message: str, assistant_message: str, uid: str | None = None) -> dict | None:
    import re

    combined = f"{user_message}\n{assistant_message}"
    for m in re.finditer(
        r'(?:idea|video about|make a video on)[:\s]+["\']?([^"\']{10,80})', combined, re.I
    ):
        title = m.group(1).strip()
        if len(title) > 8:
            return save_idea(title, provenance="chat_capture", state="seed", uid=uid)
    return None

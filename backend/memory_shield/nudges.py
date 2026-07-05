"""Proactive nudges — celebration, idea-completion, consistency only by default.

Competitor-watch is pull-only unless preferences.competitor_alerts is explicitly ON
AND a competitor outlier maps to an existing seed/planted idea (actionable, not anxiety).
"""

from __future__ import annotations

import json
from datetime import date, datetime

from .config import CACHE_DIR
from .corpus import load_corpus
from .db.models import User
from .fingerprint import load_fingerprint
from .lifecycle import list_planted, list_seeds
from .preferences import get_preferences
from .track import get_track

NUDGE_STATE_PATH = CACHE_DIR / "nudge_state.json"
MIN_HOURS_BETWEEN_PUSH = 20


def _load_state() -> dict:
    if NUDGE_STATE_PATH.exists():
        return json.loads(NUDGE_STATE_PATH.read_text())
    return {"users": {}}


def _save_state(state: dict) -> None:
    NUDGE_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1))


def _budget_allows(prefs: dict) -> bool:
    budget = prefs.get("interruption_budget", "normal")
    if budget == "low":
        return False
    return True


def _recently_sent(uid: str, kind: str, state: dict) -> bool:
    user_state = state.get("users", {}).get(uid, {})
    last = user_state.get(kind)
    if not last:
        return False
    try:
        ts = datetime.fromisoformat(last.replace("Z", ""))
    except ValueError:
        return False
    return (datetime.utcnow() - ts).total_seconds() < MIN_HOURS_BETWEEN_PUSH * 3600


def _mark_sent(uid: str, kind: str, state: dict) -> None:
    state.setdefault("users", {}).setdefault(uid, {})[kind] = datetime.utcnow().isoformat() + "Z"


def _celebration_nudge(track: dict) -> str | None:
    uploads = track.get("uploads") or []
    above = [u for u in uploads if u.get("status") == "above"]
    if not above:
        return None
    u = above[0]
    return (
        f"🌱 Your last upload ({u['title'][:45]}…) is beating your trailing baseline "
        f"at {u['ratio']}× — nice. Want to keep that momentum on something planted?"
    )


def _consistency_nudge(cadence: dict) -> str | None:
    days = cadence.get("days_since_last")
    gap = cadence.get("median_gap_days")
    if days is None or not gap:
        return None
    if days <= gap:
        return None
    overdue = days - gap
    if overdue < 3:
        return None
    return (
        f"🌱 It's been {days} days since your last post — your usual rhythm is ~{gap} days. "
        "Want to pick one planted idea to film this week?"
    )


def _idea_completion_nudge(planted: list[dict]) -> str | None:
    if not planted:
        return None
    today = date.today()
    stale = []
    for d in planted:
        planted_at = d.get("planted_at") or d.get("updated_at") or ""
        if not planted_at:
            continue
        try:
            dt = datetime.fromisoformat(planted_at.replace("Z", "")).date()
        except ValueError:
            continue
        if (today - dt).days >= 14:
            stale.append(d)
    if not stale:
        return None
    pick = stale[0]
    return (
        f"🌱 Still thinking about “{pick['title'][:50]}”? "
        "It's been a couple weeks on your board — good time to film if the angle still feels right."
    )


def _topic_overlap(a: str, b: str) -> bool:
    stop = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "your", "how", "what"}
    ta = {w for w in a.lower().split() if len(w) > 2 and w not in stop}
    tb = {w for w in b.lower().split() if len(w) > 2 and w not in stop}
    return bool(ta & tb)


def _competitor_actionable_nudge(uid: str, prefs: dict) -> str | None:
    """Opt-in only — competitor video adjacent to a seed/planted idea."""
    if not prefs.get("competitor_alerts"):
        return None

    fp = load_fingerprint()
    open_ideas = list_seeds(uid) + list_planted(uid)
    if not open_ideas:
        return None

    best = None
    for comp in fp.get("competitors", [])[:6]:
        for vid in comp.get("top_videos") or comp.get("videos") or []:
            outlier = vid.get("outlier_score") or vid.get("ratio") or 0
            if outlier < 1.8:
                continue
            title = vid.get("title") or ""
            for idea in open_ideas:
                blob = f"{idea.get('title', '')} {idea.get('angle', '')} {' '.join(idea.get('topic_labels') or [])}"
                if _topic_overlap(title, blob):
                    best = (idea, comp, vid)
                    break
            if best:
                break
        if best:
            break

    if not best:
        return None

    idea, comp, vid = best
    return (
        f"🌱 Good time to make yours — you already have “{idea['title'][:40]}” on your board, "
        f"and {comp.get('handle', 'a peer channel')} just posted something adjacent "
        f"({vid.get('title', '')[:40]}…). Pull-only signal — open check_competitors when you're ready."
    )


def _cadence() -> dict:
    from statistics import median as med

    corpus = load_corpus()
    dates = sorted(
        date.fromisoformat(v["published"])
        for v in corpus["live"] + corpus.get("holdout", [])
    )
    if len(dates) < 3:
        return {"days_since_last": None, "median_gap_days": None}
    gaps = [(b - a).days for a, b in zip(dates[-11:-1], dates[-10:])]
    days_since = (date.today() - dates[-1]).days
    return {
        "days_since_last": days_since,
        "median_gap_days": round(med(gaps)) if gaps else None,
    }


async def collect_proactive_nudges(uid: str) -> list[dict]:
    prefs = get_preferences(uid)
    if not _budget_allows(prefs):
        return []

    cadence = _cadence()
    track = await get_track()
    planted = list_planted(uid)
    out: list[dict] = []

    for kind, fn, args in (
        ("celebration", _celebration_nudge, (track,)),
        ("idea_completion", _idea_completion_nudge, (planted,)),
        ("consistency", _consistency_nudge, (cadence,)),
    ):
        msg = fn(*args)
        if msg:
            out.append({"kind": kind, "text": msg})

    msg = _competitor_actionable_nudge(uid, prefs)
    if msg:
        out.append({"kind": "competitor_actionable", "text": msg})

    return out


def _competitor_anxiety_copy(text: str) -> bool:
    """Block generic competitor-comparison push copy."""
    t = text.lower()
    blocked = [
        "they're beating you",
        "they are beating you",
        "someone else is winning",
        "competitor is overperforming",
        "competitor overperforming",
        "falling behind",
        "outperforming you",
    ]
    return any(p in t for p in blocked)


async def maybe_send_proactive_nudges(user: User) -> list[str]:
    """Send at most one earned nudge per refresh tick. Returns messages sent."""
    if not user.telegram_chat_id:
        return []

    from .telegram_bot import send_nudge_to_user

    state = _load_state()
    candidates = await collect_proactive_nudges(user.uid)
    sent: list[str] = []

    for cand in candidates:
        kind = cand["kind"]
        text = cand["text"]
        if kind == "competitor_actionable" and not get_preferences(user.uid).get("competitor_alerts"):
            continue
        if _competitor_anxiety_copy(text):
            continue
        if _recently_sent(user.uid, kind, state):
            continue
        if send_nudge_to_user(user.uid, text):
            _mark_sent(user.uid, kind, state)
            sent.append(text)
            break  # one nudge per tick — interruption budget

    _save_state(state)
    return sent

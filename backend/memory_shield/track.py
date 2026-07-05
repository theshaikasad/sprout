"""Auto-tracked performance — the improve() loop with ZERO user input.

The tool has the public numbers; the creator should never type them back in.
refresh: re-fetch live view counts for the newest uploads (one cheap
videos.list call), judge each against the channel median (linear projection
while young), and feed the delta into the graph's native feedback weights via
improve() on the video's own Topic/Format nodes — matched by label, since the
newest uploads may be holdout videos that aren't graph nodes themselves.

Incremental + idempotent: .cache/track.json remembers what was already applied
per video; only a material change (≥10 pct-points) re-weights the memory.
"""

import asyncio
import json
import time
from datetime import date
from statistics import median as med

from .config import CACHE_DIR
from .corpus import load_corpus
from .kg import Graph
from .ops import improve
from .youtube import _client, _video_details

TRACK_PATH = CACHE_DIR / "track.json"
TTL_S = 6 * 3600
N_TRACKED = 3
MIN_APPLY_PCT = 10.0  # don't churn weights on noise


def _load_state() -> dict:
    if TRACK_PATH.exists():
        return json.loads(TRACK_PATH.read_text())
    return {"checked_at": 0.0, "videos": {}, "last_result": None}


def _save_state(state: dict) -> None:
    TRACK_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1))


def _status(ratio: float, projected_ratio: float) -> str:
    if ratio >= 1:
        return "above"
    if projected_ratio >= 1:
        return "on_track"
    return "under"


async def get_track(force: bool = False) -> dict:
    state = _load_state()
    if (
        not force
        and state.get("last_result")
        and time.time() - state.get("checked_at", 0) < TTL_S
    ):
        return state["last_result"]

    corpus = load_corpus()
    mine = sorted(
        corpus["live"] + corpus["holdout"], key=lambda v: v["published"], reverse=True
    )
    tracked = mine[:N_TRACKED]
    if not tracked:
        return {"uploads": [], "improved_nodes": 0, "checked_at": time.time()}
    median = med(v["views"] for v in corpus["live"]) or 1

    try:  # live numbers; corpus snapshot is the offline fallback
        fresh_list = await asyncio.to_thread(
            _video_details, _client(), [t["video_id"] for t in tracked]
        )
        fresh = {v["video_id"]: v for v in fresh_list}
    except Exception:
        fresh = {}

    g = await Graph.load()
    topic_by_label = {p.get("label"): nid for nid, p in g.by_type("Topic")}
    format_by_name = {p.get("name"): nid for nid, p in g.by_type("Format")}

    uploads: list[dict] = []
    improved: dict = {}
    improved_labels: list[str] = []
    for t in tracked:
        vid = t["video_id"]
        views = (fresh.get(vid) or t)["views"]
        prev = state["videos"].get(vid, {})
        age_days = max((date.today() - date.fromisoformat(t["published"])).days, 1)
        ratio = views / median
        projected = (views / age_days * 30 if age_days < 30 else views) / median
        pct = max(-100.0, min(300.0, (ratio - 1) * 100))

        # write reality back into the memory — the video's own topics + format
        applied = False
        delta_pct = pct - prev.get("applied_pct", 0.0)
        if abs(delta_pct) >= MIN_APPLY_PCT:
            trace = {
                "topics": [
                    topic_by_label[l] for l in t.get("topics", []) if l in topic_by_label
                ],
                "formats": (
                    [format_by_name[t["format"]]]
                    if t.get("format") in format_by_name
                    else []
                ),
                "hooks": [],
            }
            if trace["topics"] or trace["formats"]:
                improved.update(await improve(trace, delta_pct))
                state["videos"][vid] = {"applied_pct": pct, "views": views}
                applied = True
                improved_labels.extend(t.get("topics", []))
                if t.get("format"):
                    improved_labels.append(t["format"])
        if not applied:
            state["videos"].setdefault(vid, {})["views"] = views

        uploads.append({
            "video_id": vid,
            "title": t["title"],
            "published": t["published"],
            "age_days": age_days,
            "views": views,
            "views_delta": views - prev.get("views", views),
            "ratio": round(ratio, 2),
            "projected_ratio": round(projected, 2),
            "status": _status(ratio, projected),
            "improved": applied,
        })

    above = [u for u in uploads if u["status"] == "above"]
    if above:
        u = above[0]
        headline = (
            f"Your last one ({u['title'][:40]}…) is beating your trailing baseline "
            f"at {u['ratio']}× — nice. 🎉"
        )
    elif uploads and uploads[0]["status"] == "on_track":
        headline = "Steady growth — your recent upload is on pace with your garden's rhythm."
    else:
        headline = "People are still finding you — want a planted idea to tend next?"

    result = {
        "checked_at": time.time(),
        "median_views": round(median),
        "headline": headline,
        "uploads": uploads,
        "improved_nodes": len(improved),
        "improved_labels": list(dict.fromkeys(improved_labels)),
    }
    state["checked_at"] = time.time()
    state["last_result"] = result
    _save_state(state)
    return result


if __name__ == "__main__":
    r = asyncio.run(get_track(force=True))
    print(f"median {r['median_views']} · improved {r['improved_nodes']} nodes")
    for u in r["uploads"]:
        print(
            f"  [{u['status']:>8}] {u['views']:>7} views ({u['ratio']}x, proj {u['projected_ratio']}x)"
            f" · {u['age_days']}d · improved={u['improved']} · {u['title'][:55]}"
        )

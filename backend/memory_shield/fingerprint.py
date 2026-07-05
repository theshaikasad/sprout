"""Genre fingerprint + competitor triangulation engine.

Stage 1: weighted topic×format distribution (recency-weighted by growth score).
Stage 2: true competitive set via embedding adjacency + suggested-traffic + size band.
Stage 3: competitor video ranking by outlier score × velocity × topic-match.

Run: python -m memory_shield.fingerprint
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from .analytics_fixture import load_analytics, _recency_weight
from .cold_start import (
    TIER_ESTABLISHED,
    build_cold_start_meta,
    classify_tier,
    genre_summary_for_tier,
    niche_text,
)
from .config import FINGERPRINT_PATH
from .corpus import load_corpus
from .preferences import get_preferences


def _size_band_ok(creator_subs: int, comp_subs: int) -> bool:
    if creator_subs <= 0:
        return True
    ratio = comp_subs / creator_subs
    return 0.3 <= ratio <= 10.0


def _niche_tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "your", "about"}
    return {
        w for w in re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
        if len(w) > 2 and w not in stop
    }


def build_fingerprint(
    corpus: dict | None = None,
    *,
    declared_niche: str = "",
    tier: str | None = None,
    uid: str | None = None,
) -> dict:
    corpus = corpus or load_corpus()
    analytics = load_analytics()
    per_video = analytics.get("per_video", {})
    ref = date.fromisoformat(corpus["holdout_cutoff"])

    live = corpus["live"]
    live_count = len(live)
    tier = tier or classify_tier(live_count)

    prefs = get_preferences(uid)
    declared = (declared_niche or prefs.get("declared_niche") or "").strip()

    topic_weights: dict[str, float] = {}
    format_weights: dict[str, float] = {}
    total_w = 0.0

    for v in live:
        a = per_video.get(v["video_id"], {})
        w = _recency_weight(v["published"], ref) * (a.get("growth_score") or 1)
        total_w += w
        fmt = v.get("format", "unknown")
        format_weights[fmt] = format_weights.get(fmt, 0) + w
        for t in v.get("topics", []):
            topic_weights[t] = topic_weights.get(t, 0) + w

    def normalize(d: dict[str, float]) -> dict[str, float]:
        s = sum(d.values()) or 1
        return {k: round(v / s, 4) for k, v in sorted(d.items(), key=lambda kv: -kv[1])}

    topic_dist = normalize(topic_weights)
    format_dist = normalize(format_weights)

    top_topics = list(topic_dist.keys())[:3]
    top_format = next(iter(format_dist), "personal-essay")
    genre_label = " / ".join(top_topics) if top_topics else (declared or "your niche")

    if tier != TIER_ESTABLISHED and declared and not top_topics:
        genre_label = declared

    genre_summary = genre_summary_for_tier(
        tier=tier,
        live_video_count=live_count,
        declared_niche=declared,
        genre_label=genre_label,
        dominant_format=top_format,
    )

    creator_subs = corpus["creator"].get("subscribers") or 1_650_000
    niche_tokens = _niche_tokens(
        niche_text(tier=tier, declared_niche=declared, genre_label=genre_label)
    )
    my_topics = set(topic_dist.keys()) or niche_tokens

    competitors_out = []
    for handle, vids in corpus.get("competitors", {}).items():
        try:
            from .youtube import resolve_channel
            ch = resolve_channel(handle)
            comp_subs = ch.get("subscribers") or 0
        except Exception:
            comp_subs = 0
        if not _size_band_ok(creator_subs, comp_subs):
            continue

        suggested_hits = sum(
            1 for v in live
            if per_video.get(v["video_id"], {}).get("traffic_sources", {}).get("suggested_adjacent_channel") == handle
        )

        comp_topics: dict[str, int] = {}
        for v in vids:
            for t in v.get("topics", []):
                comp_topics[t] = comp_topics.get(t, 0) + 1
        overlap = my_topics & set(comp_topics.keys())
        if not overlap and niche_tokens:
            overlap = {
                t for t in comp_topics
                if _niche_tokens(t) & niche_tokens
            }
        overlap_score = len(overlap) / max(len(my_topics), 1)

        comp_views = [v.get("views", 0) for v in vids]
        comp_median = sorted(comp_views)[len(comp_views) // 2] if comp_views else 1

        ranked_vids = []
        for v in vids:
            views = v.get("views", 0)
            days_old = max(1, (date.today() - date.fromisoformat(v["published"][:10])).days)
            velocity = views / days_old
            outlier = views / max(comp_median, 1)
            topic_match = "in_lane" if set(v.get("topics", [])) & my_topics else "adjacent"
            ranked_vids.append({
                "video_id": v["video_id"],
                "title": v["title"],
                "views": views,
                "outlier_score": round(outlier, 2),
                "velocity": round(velocity, 1),
                "topic_match": topic_match,
                "published": v["published"],
            })
        ranked_vids.sort(key=lambda x: -(x["outlier_score"] * 0.6 + x["velocity"] * 0.0001))

        tri_score = overlap_score * 0.5 + min(suggested_hits / 5, 1) * 0.3 + (0.2 if comp_subs else 0)
        competitors_out.append({
            "handle": handle,
            "subscribers": comp_subs,
            "topic_overlap": sorted(overlap)[:6],
            "overlap_score": round(overlap_score, 3),
            "suggested_traffic_hits": suggested_hits,
            "triangulation_score": round(tri_score, 3),
            "top_videos": ranked_vids[:4],
        })

    competitors_out.sort(key=lambda c: -c["triangulation_score"])

    cold_start = build_cold_start_meta(
        tier=tier,
        live_video_count=live_count,
        declared_niche=declared,
        genre_label=genre_label,
    )

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "creator_handle": corpus["creator"].get("handle"),
        "cold_start": cold_start,
        "genre": {
            "label": genre_label,
            "summary": genre_summary,
            "topic_distribution": topic_dist,
            "format_distribution": format_dist,
            "dominant_format": top_format,
        },
        "competitors": competitors_out,
        "creator_subscribers": creator_subs,
    }
    _persist_fingerprint(payload, uid=uid)
    return payload


def _persist_fingerprint(payload: dict, uid: str | None = None) -> None:
    from .db.context import require_uid
    from .db.models import Fingerprint
    from .db.sync_session import sync_session

    uid = uid or require_uid()
    with sync_session() as session:
        fp = session.get(Fingerprint, uid)
        if not fp:
            fp = Fingerprint(uid=uid)
        fp.generated_at = datetime.utcnow()
        fp.payload = payload
        session.add(fp)
        session.commit()
    FINGERPRINT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1))


def load_fingerprint(uid: str | None = None) -> dict:
    from .db.context import require_uid
    from .db.models import Fingerprint
    from .db.sync_session import sync_session

    uid = uid or require_uid()
    try:
        with sync_session() as session:
            fp = session.get(Fingerprint, uid)
            if fp and fp.payload:
                return fp.payload
    except Exception:
        pass
    if FINGERPRINT_PATH.exists():
        return json.loads(FINGERPRINT_PATH.read_text())
    return build_fingerprint()


def load_cold_start(uid: str | None = None) -> dict:
    fp = load_fingerprint(uid)
    cs = fp.get("cold_start")
    if cs:
        return cs
    live_count = len(load_corpus().get("live", []))
    tier = classify_tier(live_count)
    prefs = get_preferences(uid)
    return build_cold_start_meta(
        tier=tier,
        live_video_count=live_count,
        declared_niche=prefs.get("declared_niche", ""),
        genre_label=fp.get("genre", {}).get("label", ""),
    )


if __name__ == "__main__":
    fp = build_fingerprint()
    print(f"genre: {fp['genre']['label']}")
    print(f"summary: {fp['genre']['summary']}")
    print(f"tier: {fp['cold_start']['tier']}")
    print(f"competitors: {len(fp['competitors'])}")
    for c in fp["competitors"][:3]:
        print(f"  {c['handle']} score={c['triangulation_score']} overlap={c['topic_overlap'][:2]}")

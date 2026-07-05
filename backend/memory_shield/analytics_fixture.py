"""Synthetic analytics fixture — fabricated-but-internally-consistent per-video metrics.

Deterministic from real public view counts + video features. Encodes Lana's loud
pre-cutoff pattern (personal/vulnerable essays outperform listicles/vlogs) so the
backtest reveal lands. All baselines are trailing/recency-weighted.

Run: python -m memory_shield.analytics_fixture
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime

from .config import (
    ANALYTICS_PATH,
    ANALYTICS_TABLE_PATH,
    HOLDOUT_CUTOFF,
    RECENCY_HALF_LIFE_DAYS,
)
from .corpus import CORPUS_PATH, load_corpus

# Title/topic heuristics for Lana's conversion fingerprint
_VULNERABLE_MARKERS = re.compile(
    r"(?i)\b(deaf|hearing|single|ghost|lonely|anxiety|vulnerable|lost|grief|"
    r"almost\s+30|mental|breakup|healing|confession|honest|raw|real\s+talk)\b"
)
_LISTICLE_MARKERS = re.compile(
    r"(?i)\b(\d+\s+(things|habits|ways|tips|rules)|morning\s+routine|"
    r"productivity|habits?\s+that|things\s+i\s+do)\b"
)


def _seed(video_id: str) -> int:
    return int(hashlib.md5(video_id.encode()).hexdigest()[:8], 16)


def _recency_weight(published: str, ref: date | None = None) -> float:
    ref = ref or date.today()
    try:
        pub = date.fromisoformat(published[:10])
    except ValueError:
        return 0.5
    days = max(0, (ref - pub).days)
    return math.exp(-days * math.log(2) / RECENCY_HALF_LIFE_DAYS)


def _content_multiplier(video: dict) -> float:
    """Higher = converts better. Encodes vulnerable-essay > vlog/listicle."""
    title = video.get("title", "")
    fmt = video.get("format", "")
    topics = " ".join(video.get("topics", []))
    blob = f"{title} {topics}"

    if _VULNERABLE_MARKERS.search(blob) or fmt == "personal-essay":
        base = 2.8 + (_seed(video["video_id"]) % 700) / 1000  # ~2.8–3.5×
    elif fmt in ("listicle", "day-in-life") or _LISTICLE_MARKERS.search(blob):
        base = 0.55 + (_seed(video["video_id"]) % 250) / 1000  # ~0.55–0.8×
    elif fmt == "vlog":
        base = 0.75 + (_seed(video["video_id"]) % 300) / 1000
    else:
        base = 1.0 + (_seed(video["video_id"]) % 400) / 1000 - 0.2

    if video.get("is_short"):
        base *= 0.85 + (_seed(video["video_id"] + "s") % 300) / 1000
    return base


def _retention_curve(video: dict, avg_view_pct: float) -> list[dict]:
    """60-point retention curve aligned to beats."""
    duration = max(video.get("duration_seconds") or 60, 1)
    beats = video.get("beats") or [{"type": "story", "start_sec": 0, "end_sec": duration}]
    points = []
    for i in range(60):
        t = i / 59 * duration
        beat = next((b for b in beats if b["start_sec"] <= t <= b["end_sec"]), beats[-1])
        btype = beat.get("type", "story")
        # Beat-type retention modifiers
        mod = {
            "intro": 0.92, "context": 0.88, "story": 1.0, "demo": 0.95,
            "sponsor": 0.72, "cta": 0.78, "outro": 0.85,
        }.get(btype, 0.9)
        decay = 1.0 - (t / duration) * (1.0 - avg_view_pct / 100) * 0.6
        pct = max(5, min(100, avg_view_pct * mod * decay * 100 / avg_view_pct if avg_view_pct else decay * 100))
        points.append({"sec": round(t, 1), "pct": round(pct, 1)})
    return points


def _traffic_sources(video: dict, competitors: dict) -> dict[str, float]:
    """Synthetic traffic mix; suggested-video points at competitor channels."""
    seed = _seed(video["video_id"] + "traffic")
    comp_handles = list(competitors.keys())
    suggested_target = comp_handles[seed % len(comp_handles)] if comp_handles else ""
    base = {
        "browse": 0.18 + (seed % 80) / 1000,
        "suggested": 0.28 + (seed % 120) / 1000,
        "search": 0.22 + (seed % 90) / 1000,
        "external": 0.08 + (seed % 40) / 1000,
        "channel": 0.14 + (seed % 60) / 1000,
        "other": 0.10,
    }
    total = sum(base.values())
    out = {k: round(v / total, 3) for k, v in base.items()}
    out["suggested_adjacent_channel"] = suggested_target
    return out


def _video_analytics(video: dict, baseline_views: float, competitors: dict) -> dict:
    mult = _content_multiplier(video)
    views = video.get("views") or 1
    ratio = views / max(baseline_views, 1)

    seed = _seed(video["video_id"])
    # Anchor synthetic metrics to real views + content multiplier
    impressions = int(views / (0.045 + (seed % 30) / 1000) * mult ** 0.3)
    ctr = round((0.035 + (seed % 25) / 1000) * mult ** 0.4, 4)
    avg_view_pct = round(min(72, max(18, 42 * mult ** 0.35 + (seed % 80) / 10)), 1)
    subs_gained = int(views * 0.002 * mult ** 0.5)
    watch_hours = round(views * (video.get("duration_seconds") or 600) / 3600 * avg_view_pct / 100, 1)

    growth_score = round(
        subs_gained * 3 + avg_view_pct * 2 + ctr * 1000 + watch_hours * 0.1,
        2,
    )

    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "published": video["published"],
        "is_short": video.get("is_short", False),
        "format": video.get("format", ""),
        "topics": video.get("topics", []),
        "hook_style": (video.get("hook") or {}).get("style", ""),
        "views": views,
        "ratio_vs_baseline": round(ratio, 2),
        "content_multiplier": round(mult, 3),
        "impressions": impressions,
        "ctr": ctr,
        "avg_view_percentage": avg_view_pct,
        "subs_gained": subs_gained,
        "watch_hours": watch_hours,
        "growth_score": growth_score,
        "retention_curve": _retention_curve(video, avg_view_pct),
        "traffic_sources": _traffic_sources(video, competitors),
        "best_publish_hour_utc": 14 + seed % 8,
        "audience_female_pct": round(0.62 + (seed % 80) / 1000, 3),
        "audience_age_25_34_pct": round(0.38 + (seed % 120) / 1000, 3),
    }


def _recency_weighted_baseline(videos: list[dict], ref: date | None = None) -> float:
    if not videos:
        return 1.0
    num = den = 0.0
    for v in videos:
        w = _recency_weight(v["published"], ref)
        num += v.get("views", 0) * w
        den += w
    return num / den if den else 1.0


def build_analytics(corpus: dict | None = None) -> dict:
    corpus = corpus or load_corpus()
    ref = date.fromisoformat(corpus["holdout_cutoff"]) if corpus.get("holdout_cutoff") else HOLDOUT_CUTOFF

    creator_videos = corpus["live"] + corpus["holdout"]
    baseline_long = _recency_weighted_baseline(
        [v for v in creator_videos if not v.get("is_short")], ref
    )
    baseline_short = _recency_weighted_baseline(
        [v for v in creator_videos if v.get("is_short")], ref
    ) or baseline_long

    per_video: dict[str, dict] = {}
    table_rows: list[dict] = []

    def process(videos: list[dict], baseline: float):
        for v in videos:
            row = _video_analytics(v, baseline, corpus.get("competitors", {}))
            per_video[v["video_id"]] = row
            table_rows.append({
                "video_id": v["video_id"],
                "title": v["title"],
                "published": v["published"],
                "is_short": v.get("is_short", False),
                "format": v.get("format", ""),
                "topics": v.get("topics", []),
                "hook_style": (v.get("hook") or {}).get("style", ""),
                "views": v.get("views", 0),
                "impressions": row["impressions"],
                "ctr": row["ctr"],
                "avg_view_percentage": row["avg_view_percentage"],
                "subs_gained": row["subs_gained"],
                "watch_hours": row["watch_hours"],
                "growth_score": row["growth_score"],
                "ratio_vs_baseline": row["ratio_vs_baseline"],
                "content_multiplier": row["content_multiplier"],
            })

    process([v for v in creator_videos if not v.get("is_short")], baseline_long)
    process([v for v in creator_videos if v.get("is_short")], baseline_short)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "holdout_cutoff": corpus.get("holdout_cutoff"),
        "baselines": {
            "long_form_views": round(baseline_long),
            "short_form_views": round(baseline_short),
            "method": "recency_weighted",
            "half_life_days": RECENCY_HALF_LIFE_DAYS,
        },
        "per_video": per_video,
    }
    _persist_analytics(payload, table_rows)
    return payload


def _persist_analytics(payload: dict, table_rows: list[dict], uid: str | None = None) -> None:
    from .db.context import require_uid
    from .db.models import AnalyticsMeta, AnalyticsVideo
    from .db.sync_session import sync_session

    uid = uid or require_uid()
    with sync_session() as session:
        from sqlmodel import select
        old = session.exec(select(AnalyticsVideo).where(AnalyticsVideo.uid == uid)).all()
        for row in old:
            session.delete(row)
        meta = session.get(AnalyticsMeta, uid)
        if not meta:
            meta = AnalyticsMeta(uid=uid)
        meta.generated_at = datetime.utcnow()
        hc = payload.get("holdout_cutoff")
        meta.holdout_cutoff = date.fromisoformat(hc) if isinstance(hc, str) else hc
        meta.baselines = payload.get("baselines", {})
        session.add(meta)
        for row in table_rows:
            pv = payload["per_video"][row["video_id"]]
            session.add(AnalyticsVideo(
                uid=uid,
                video_id=row["video_id"],
                title=row["title"],
                published=row["published"],
                is_short=row["is_short"],
                format=row["format"],
                topics=row["topics"],
                hook_style=row["hook_style"],
                views=row["views"],
                impressions=row["impressions"],
                ctr=row["ctr"],
                avg_view_percentage=row["avg_view_percentage"],
                subs_gained=row["subs_gained"],
                watch_hours=row["watch_hours"],
                growth_score=row["growth_score"],
                ratio_vs_baseline=row["ratio_vs_baseline"],
                content_multiplier=row["content_multiplier"],
                retention_curve=pv.get("retention_curve", []),
                traffic_sources=pv.get("traffic_sources", {}),
            ))
        session.commit()
    # Legacy JSON mirror for demo/dev fallback
    ANALYTICS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    ANALYTICS_TABLE_PATH.write_text(json.dumps(table_rows, ensure_ascii=False, indent=1))


def load_analytics(uid: str | None = None) -> dict:
    from .db.context import require_uid
    from .db.models import AnalyticsMeta, AnalyticsVideo
    from .db.sync_session import sync_session
    from sqlmodel import select

    uid = uid or require_uid()
    try:
        with sync_session() as session:
            meta = session.get(AnalyticsMeta, uid)
            if meta:
                rows = session.exec(select(AnalyticsVideo).where(AnalyticsVideo.uid == uid)).all()
                per_video = {}
                for v in rows:
                    per_video[v.video_id] = {
                        "video_id": v.video_id,
                        "title": v.title,
                        "published": v.published,
                        "is_short": v.is_short,
                        "format": v.format,
                        "topics": v.topics,
                        "hook_style": v.hook_style,
                        "views": v.views,
                        "impressions": v.impressions,
                        "ctr": v.ctr,
                        "avg_view_percentage": v.avg_view_percentage,
                        "subs_gained": v.subs_gained,
                        "watch_hours": v.watch_hours,
                        "growth_score": v.growth_score,
                        "ratio_vs_baseline": v.ratio_vs_baseline,
                        "content_multiplier": v.content_multiplier,
                        "retention_curve": v.retention_curve,
                        "traffic_sources": v.traffic_sources,
                    }
                return {
                    "generated_at": meta.generated_at.isoformat() + "Z",
                    "holdout_cutoff": str(meta.holdout_cutoff) if meta.holdout_cutoff else None,
                    "baselines": meta.baselines,
                    "per_video": per_video,
                }
    except Exception:
        pass
    if ANALYTICS_PATH.exists():
        return json.loads(ANALYTICS_PATH.read_text())
    if CORPUS_PATH.exists():
        return build_analytics()
    raise FileNotFoundError("Run corpus build first, then analytics")


def load_analytics_table() -> list[dict]:
    if not ANALYTICS_TABLE_PATH.exists():
        build_analytics()
    return json.loads(ANALYTICS_TABLE_PATH.read_text())


if __name__ == "__main__":
    data = build_analytics()
    n = len(data["per_video"])
    print(f"analytics: {n} videos")
    print(f"baselines: long={data['baselines']['long_form_views']} short={data['baselines']['short_form_views']}")
    print(f"written: {ANALYTICS_PATH}")

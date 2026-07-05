"""Real YouTube Analytics API ingestion — same output shape as analytics_fixture."""

from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime

from .analytics_fixture import (
    _persist_analytics,
    _recency_weighted_baseline,
    build_analytics,
    load_analytics,
)
from .config import HOLDOUT_CUTOFF, RECENCY_HALF_LIFE_DAYS
from .corpus import load_corpus


def _analytics_get(access_token: str, params: dict) -> dict:
    qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    url = f"https://youtubeanalytics.googleapis.com/v2/reports?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _fetch_video_metrics(access_token: str, channel_id: str, video_id: str, start: str, end: str) -> dict:
    """Retention, CTR/impressions, traffic sources for one video."""
    out: dict = {"retention_curve": [], "traffic_sources": {}, "impressions": 0, "ctr": 0.0}

    try:
        r = _analytics_get(access_token, {
            "ids": f"channel=={channel_id}",
            "startDate": start,
            "endDate": end,
            "metrics": "averageViewPercentage",
            "dimensions": "elapsedVideoTimeRatio",
            "filters": f"video=={video_id}",
            "sort": "elapsedVideoTimeRatio",
        })
        rows = r.get("rows") or []
        out["retention_curve"] = [
            {"sec": round(float(row[0]) * 100, 1), "pct": round(float(row[1]), 1)}
            for row in rows
        ]
        if out["retention_curve"]:
            out["avg_view_percentage"] = round(
                sum(p["pct"] for p in out["retention_curve"]) / len(out["retention_curve"]), 1
            )
    except Exception as e:
        print(f"analytics_youtube: retention {video_id} — {e}")

    try:
        r = _analytics_get(access_token, {
            "ids": f"channel=={channel_id}",
            "startDate": start,
            "endDate": end,
            "metrics": "impressions,ctr",
            "dimensions": "video",
            "filters": f"video=={video_id}",
        })
        if r.get("rows"):
            out["impressions"] = int(r["rows"][0][1] or 0)
            out["ctr"] = float(r["rows"][0][2] or 0)
    except Exception as e:
        print(f"analytics_youtube: ctr {video_id} — {e}")

    try:
        r = _analytics_get(access_token, {
            "ids": f"channel=={channel_id}",
            "startDate": start,
            "endDate": end,
            "metrics": "views",
            "dimensions": "insightTrafficSourceType",
            "filters": f"video=={video_id}",
        })
        rows = r.get("rows") or []
        total = sum(int(row[1] or 0) for row in rows) or 1
        out["traffic_sources"] = {
            row[0].lower().replace(" ", "_"): round(int(row[1] or 0) / total, 3)
            for row in rows
        }
    except Exception as e:
        print(f"analytics_youtube: traffic {video_id} — {e}")

    return out


def build_analytics_real(
    access_token: str,
    channel_id: str,
    corpus: dict | None = None,
    uid: str | None = None,
) -> dict:
    """Pull real Analytics API metrics; fall back to fixture fields where API returns empty."""
    corpus = corpus or load_corpus()
    ref = date.fromisoformat(corpus["holdout_cutoff"]) if corpus.get("holdout_cutoff") else HOLDOUT_CUTOFF
    end = date.today().isoformat()
    start = ref.isoformat()

    creator_videos = corpus["live"] + corpus["holdout"]
    baseline_long = _recency_weighted_baseline(
        [v for v in creator_videos if not v.get("is_short")], ref
    )
    baseline_short = _recency_weighted_baseline(
        [v for v in creator_videos if v.get("is_short")], ref
    ) or baseline_long

    # Start from fixture for derived fields, overlay real API where available
    fixture = build_analytics(corpus)
    per_video = dict(fixture["per_video"])

    for v in creator_videos:
        vid = v["video_id"]
        real = _fetch_video_metrics(access_token, channel_id, vid, start, end)
        row = per_video.get(vid, {})
        if real.get("retention_curve"):
            row["retention_curve"] = real["retention_curve"]
        if real.get("avg_view_percentage"):
            row["avg_view_percentage"] = real["avg_view_percentage"]
        if real.get("impressions"):
            row["impressions"] = real["impressions"]
        if real.get("ctr"):
            row["ctr"] = real["ctr"]
        if real.get("traffic_sources"):
            row["traffic_sources"] = real["traffic_sources"]
        per_video[vid] = row

    table_rows = [
        {
            "video_id": vid,
            "title": row["title"],
            "published": row["published"],
            "is_short": row.get("is_short", False),
            "format": row.get("format", ""),
            "topics": row.get("topics", []),
            "hook_style": row.get("hook_style", ""),
            "views": row.get("views", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "avg_view_percentage": row.get("avg_view_percentage", 0),
            "subs_gained": row.get("subs_gained", 0),
            "watch_hours": row.get("watch_hours", 0),
            "growth_score": row.get("growth_score", 0),
            "ratio_vs_baseline": row.get("ratio_vs_baseline", 0),
            "content_multiplier": row.get("content_multiplier", 1),
        }
        for vid, row in per_video.items()
    ]

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "holdout_cutoff": corpus.get("holdout_cutoff"),
        "baselines": fixture["baselines"],
        "per_video": per_video,
        "source": "youtube_analytics_api",
    }
    _persist_analytics(payload, table_rows, uid=uid)
    return payload

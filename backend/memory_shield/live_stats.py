"""Near-live view counts via YouTube Data API polling."""

from __future__ import annotations

from datetime import datetime, timedelta

from googleapiclient.discovery import build

from .config import YOUTUBE_API_KEY
from .db.context import require_uid
from .db.models import VideoStatsSnapshot
from .db.sync_session import sync_session
from .corpus import load_corpus
from sqlmodel import select


def _client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)


def poll_live_stats(uid: str | None = None, lookback_days: int = 14) -> list[dict]:
    """Snapshot views/likes for recent uploads; return deltas vs previous snapshot."""
    uid = uid or require_uid()
    corpus = load_corpus()
    cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).date()
    recent = [
        v for v in corpus.get("live", [])
        if v.get("published", "")[:10] >= cutoff.isoformat()
    ]
    if not recent:
        return []

    ids = [v["video_id"] for v in recent]
    yt = _client()
    stats: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        resp = yt.videos().list(part="statistics", id=",".join(batch)).execute()
        for item in resp.get("items", []):
            st = item.get("statistics", {})
            stats[item["id"]] = {
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
            }

    now = datetime.utcnow()
    deltas = []
    with sync_session() as session:
        for v in recent:
            vid = v["video_id"]
            cur = stats.get(vid, {})
            prev = session.exec(
                select(VideoStatsSnapshot)
                .where(VideoStatsSnapshot.uid == uid, VideoStatsSnapshot.video_id == vid)
                .order_by(VideoStatsSnapshot.captured_at.desc())
            ).first()
            snap = VideoStatsSnapshot(
                uid=uid,
                video_id=vid,
                views=cur.get("views", 0),
                likes=cur.get("likes", 0),
                comments=cur.get("comments", 0),
                captured_at=now,
            )
            session.add(snap)
            if prev:
                dv = cur.get("views", 0) - prev.views
                if dv > 0:
                    deltas.append({
                        "video_id": vid,
                        "title": v.get("title", ""),
                        "views_delta": dv,
                        "views": cur.get("views", 0),
                    })
        session.commit()
    return deltas

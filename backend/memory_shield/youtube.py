"""YouTube Data API v3 fetch layer (spec §6 steps 1 + 4).

Public Data API only (spec §2 — no OAuth/Analytics). Every normalized result is
cached to disk so re-runs cost zero quota.
"""

from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from . import cache
from .config import SHORT_MAX_SECONDS, TREND_LOOKBACK_DAYS, YOUTUBE_API_KEY


def _client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)


def _parse_duration(iso: str) -> int:
    """ISO 8601 PT#H#M#S -> total seconds."""
    if not iso or not iso.startswith("PT"):
        return 0
    h = m = s = 0
    num = ""
    for ch in iso[2:]:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            h = int(num or 0)
            num = ""
        elif ch == "M":
            m = int(num or 0)
            num = ""
        elif ch == "S":
            s = int(num or 0)
            num = ""
    return h * 3600 + m * 60 + s


def _normalize(item: dict) -> dict:
    """videos().list item -> the flat shape everything downstream consumes."""
    sn, st = item["snippet"], item.get("statistics", {})
    content = item.get("contentDetails", {})
    duration_seconds = _parse_duration(content.get("duration", ""))
    return {
        "video_id": item["id"],
        "title": sn["title"],
        "description": sn.get("description", ""),
        "published": sn["publishedAt"][:10],  # ISO date
        "channel_id": sn["channelId"],
        "channel_title": sn["channelTitle"],
        "tags": sn.get("tags", []),
        "views": int(st.get("viewCount", 0)),
        "likes": int(st.get("likeCount", 0)),
        "comments": int(st.get("commentCount", 0)),
        "duration_seconds": duration_seconds,
        "is_short": duration_seconds > 0 and duration_seconds <= SHORT_MAX_SECONDS,
    }


def _video_details(yt, video_ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(video_ids), 50):
        resp = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids[i : i + 50]),
            maxResults=50,
        ).execute()
        out.extend(_normalize(it) for it in resp.get("items", []))
    return out


def resolve_channel(handle: str) -> dict:
    """@handle -> {channel_id, title, uploads_playlist, subscribers, video_count}."""
    if (hit := cache.get("youtube", f"channel_{handle}")) is not None:
        return hit
    resp = _client().channels().list(
        part="snippet,contentDetails,statistics", forHandle=handle
    ).execute()
    item = resp["items"][0]
    thumbs = item["snippet"].get("thumbnails", {})
    return cache.put("youtube", f"channel_{handle}", {
        "channel_id": item["id"],
        "title": item["snippet"]["title"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "subscribers": int(item["statistics"].get("subscriberCount", 0)),
        "video_count": int(item["statistics"].get("videoCount", 0)),
        "avatar": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
    })


def channel_videos(handle: str, limit: int) -> list[dict]:
    """Most recent `limit` uploads for a channel handle, newest first."""
    key = f"uploads_{handle}_{limit}"
    if (hit := cache.get("youtube", key)) is not None:
        return hit
    yt = _client()
    ch = resolve_channel(handle)
    ids, page = [], None
    while len(ids) < limit:
        resp = yt.playlistItems().list(
            part="contentDetails", playlistId=ch["uploads_playlist"],
            maxResults=min(50, limit - len(ids)), pageToken=page,
        ).execute()
        ids.extend(it["contentDetails"]["videoId"] for it in resp.get("items", []))
        if not (page := resp.get("nextPageToken")):
            break
    return cache.put("youtube", key, _video_details(yt, ids[:limit]))


def trend_videos(keyword: str, limit: int) -> list[dict]:
    """Top-viewed videos for a niche keyword in the last TREND_LOOKBACK_DAYS."""
    key = f"trend_{keyword}_{limit}"
    if (hit := cache.get("youtube", key)) is not None:
        return hit
    after = (datetime.now(timezone.utc) - timedelta(days=TREND_LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    resp = _client().search().list(
        part="id", q=keyword, type="video", order="viewCount",
        publishedAfter=after, relevanceLanguage="en",
        maxResults=min(limit * 3, 50),
    ).execute()
    ids = [it["id"]["videoId"] for it in resp.get("items", [])]
    videos = _video_details(_client(), ids)
    return cache.put("youtube", key, videos[:limit])

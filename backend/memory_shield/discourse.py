"""Discourse radar — Reddit + Hacker News × creator fingerprint.

Replaces generic pulse with niche-scoped discourse signals.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta

from . import cache
from .config import NICHE
from .fingerprint import load_fingerprint

# Subreddits derived from slow-living fingerprint
DEFAULT_SUBREDDITS = [
    "simpleliving", "selfimprovement", "getdisciplined",
    "DecidingToBeBetter", "minimalism",
]


def _fetch_json(url: str, timeout: int = 8) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "Sprout/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _hn_stories(limit: int = 8) -> list[dict]:
    hit = cache.get("discourse", "hn")
    if hit is not None:
        return hit
    try:
        ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")[:limit * 2]
        stories = []
        for sid in ids:
            item = _fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            if item and item.get("title"):
                stories.append({
                    "source": "hackernews",
                    "title": item["title"],
                    "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "score": item.get("score", 0),
                })
            if len(stories) >= limit:
                break
        return cache.put("discourse", "hn", stories)
    except Exception:
        return []


def _reddit_posts(subreddit: str, limit: int = 5) -> list[dict]:
    key = f"reddit_{subreddit}"
    hit = cache.get("discourse", key)
    if hit is not None:
        return hit
    try:
        data = _fetch_json(f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}")
        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            posts.append({
                "source": f"reddit/r/{subreddit}",
                "title": p.get("title", ""),
                "url": f"https://reddit.com{p.get('permalink', '')}",
                "score": p.get("score", 0),
            })
        return cache.put("discourse", key, posts)
    except Exception:
        return []


def _fit_score(title: str, fingerprint_topics: set[str]) -> float:
    words = set(title.lower().split())
    hits = sum(1 for t in fingerprint_topics if any(w in t for w in words))
    return round(hits / max(len(fingerprint_topics), 1), 2)


def build_discourse() -> dict:
    try:
        fp = load_fingerprint()
        topics = set(fp.get("genre", {}).get("topic_distribution", {}).keys())
    except Exception:
        topics = set()

    items = []
    for sub in DEFAULT_SUBREDDITS:
        for p in _reddit_posts(sub, 3):
            p["fit"] = _fit_score(p["title"], topics)
            items.append(p)
    for s in _hn_stories(6):
        s["fit"] = _fit_score(s["title"], topics)
        items.append(s)

    items.sort(key=lambda x: (-x.get("fit", 0), -x.get("score", 0)))
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "niche": NICHE,
        "items": items[:16],
    }


async def get_discourse() -> dict:
    import asyncio
    return await asyncio.to_thread(build_discourse)

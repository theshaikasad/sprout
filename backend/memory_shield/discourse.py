"""Discourse radar — Reddit + niche news × creator fingerprint.

Reddit's JSON API is blocked from most server IPs (403); RSS still works.
HN top stories are irrelevant for the slow-living demo niche — dropped.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote

from . import cache
from .config import DISCOURSE_NEWS_QUERY, DISCOURSE_SUBREDDITS, NICHE
from .fingerprint import load_fingerprint

_ATOM = "http://www.w3.org/2005/Atom"
_UA = "Mozilla/5.0 (compatible; Sprout/1.0; +https://sprout.asad.codes)"


def _fetch_bytes(url: str, timeout: int = 8) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _reddit_posts(subreddit: str, limit: int = 5) -> list[dict]:
    key = f"reddit_{subreddit}"
    hit = cache.get("discourse", key)
    if hit is not None:
        return hit
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit={limit}"
        root = ET.fromstring(_fetch_bytes(url))
        posts = []
        for entry in root.findall(f"{{{_ATOM}}}entry")[:limit]:
            title_el = entry.find(f"{{{_ATOM}}}title")
            link_el = entry.find(f"{{{_ATOM}}}link")
            title = (title_el.text or "").strip() if title_el is not None else ""
            href = link_el.get("href", "") if link_el is not None else ""
            if title:
                posts.append({
                    "source": f"reddit/r/{subreddit}",
                    "title": title,
                    "url": href,
                    "score": 0,
                })
        return cache.put("discourse", key, posts)
    except Exception:
        return []


def _niche_news(limit: int = 6) -> list[dict]:
    hit = cache.get("discourse", "niche_news")
    if hit is not None:
        return hit
    try:
        url = (
            "https://news.google.com/rss/search?q="
            + quote(DISCOURSE_NEWS_QUERY)
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        root = ET.fromstring(_fetch_bytes(url))
        items = []
        for it in root.iter("item"):
            title = (it.findtext("title") or "").rsplit(" - ", 1)[0].strip()
            link = (it.findtext("link") or "").strip()
            source = (it.findtext("source") or "news").strip()
            if title:
                items.append({
                    "source": f"news/{source[:24]}",
                    "title": title,
                    "url": link,
                    "score": 0,
                })
            if len(items) >= limit:
                break
        return cache.put("discourse", "niche_news", items)
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
    for sub in DISCOURSE_SUBREDDITS:
        for p in _reddit_posts(sub, 3):
            p["fit"] = _fit_score(p["title"], topics)
            items.append(p)
    for n in _niche_news(6):
        n["fit"] = _fit_score(n["title"], topics)
        items.append(n)

    items.sort(key=lambda x: (-x.get("fit", 0), -x.get("score", 0)))
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "niche": NICHE,
        "items": items[:16],
    }


async def get_discourse() -> dict:
    import asyncio

    return await asyncio.to_thread(build_discourse)

"""Cross-platform niche pulse — what the niche is talking about beyond YouTube.

Awareness layer only (nothing here is ingested into the graph — YouTube stays
the single ingested stream): Hacker News (Algolia API), GitHub trending new
repos (search API), Google News RSS. All free, no keys. (Reddit hard-blocks
unauthenticated JSON now — GitHub is the better dev-niche signal anyway.)
Cached to disk so the Today view is instant and no source gets hammered; a dead
source degrades to the others instead of failing the route.

CLI check: python -m memory_shield.pulse
"""

import json
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import CACHE_DIR

PULSE_PATH = CACHE_DIR / "pulse.json"
TTL_S = 45 * 60
_TIMEOUT = 8

# Niche-scoped queries (AI/ML engineering education). Tight on purpose.
HN_QUERIES = ["LLM agents", "RAG", "fine-tuning LLM", "MCP"]
GITHUB_LOOKBACK_DAYS = 14
NEWS_QUERY = '"AI agents" OR "large language models" when:2d'

PER_SOURCE = 5


def _get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "MemoryShield/0.1 (hackathon demo)"})
    with urlopen(req, timeout=_TIMEOUT) as r:
        return r.read()


def _age_h(ts: float) -> float:
    return round(max(time.time() - ts, 0) / 3600, 1)


def _hackernews() -> list[dict]:
    cutoff = int(time.time()) - 3 * 86400
    seen: dict[str, dict] = {}
    for q in HN_QUERIES:
        url = (
            "https://hn.algolia.com/api/v1/search?tags=story"
            f"&numericFilters=created_at_i>{cutoff}&hitsPerPage=4&query={quote(q)}"
        )
        for h in json.loads(_get(url)).get("hits", []):
            disc = f"https://news.ycombinator.com/item?id={h['objectID']}"
            seen[h["objectID"]] = {
                "source": "hackernews",
                "tag": "HN",
                "title": h.get("title") or "",
                "url": h.get("url") or disc,
                "discussion": disc,
                "score": h.get("points") or 0,
                "comments": h.get("num_comments") or 0,
                "age_hours": _age_h(h.get("created_at_i") or time.time()),
            }
    # same story gets submitted twice — keep the higher-scored copy per title
    by_title: dict[str, dict] = {}
    for v in seen.values():
        key = v["title"].lower().strip()
        if key and (key not in by_title or v["score"] > by_title[key]["score"]):
            by_title[key] = v
    items = sorted(by_title.values(), key=lambda i: -i["score"])
    return items[:PER_SOURCE]


def _github() -> list[dict]:
    """Brand-new repos exploding in stars — video material for a dev niche."""
    since = (date.today() - timedelta(days=GITHUB_LOOKBACK_DAYS)).isoformat()
    url = (
        "https://api.github.com/search/repositories?"
        f"q={quote(f'created:>{since} topic:ai')}"
        f"&sort=stars&order=desc&per_page={PER_SOURCE}"
    )
    items = []
    for r in json.loads(_get(url)).get("items", []):
        desc = (r.get("description") or "").strip()
        created = r.get("created_at")  # ISO8601 Z
        try:
            age = _age_h(datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp())
        except Exception:
            age = 0.0
        items.append({
            "source": "github",
            "tag": "GitHub",
            "title": f"{r['name']} — {desc}" if desc else r["full_name"],
            "url": r.get("html_url") or "",
            "discussion": None,
            "score": r.get("stargazers_count") or 0,
            "comments": None,
            "age_hours": age,
        })
    return items


def _news() -> list[dict]:
    url = (
        "https://news.google.com/rss/search?q=" + quote(NEWS_QUERY)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    root = ET.fromstring(_get(url))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").rsplit(" - ", 1)[0]
        pub = it.findtext("pubDate")
        try:
            age = _age_h(parsedate_to_datetime(pub).timestamp()) if pub else 0.0
        except Exception:
            age = 0.0
        items.append({
            "source": "news",
            "tag": it.findtext("source") or "news",
            "title": title,
            "url": it.findtext("link") or "",
            "discussion": None,
            "score": None,
            "comments": None,
            "age_hours": age,
        })
        if len(items) >= PER_SOURCE:
            break
    return items


def _interleave(*lists: list[dict]) -> list[dict]:
    out = []
    for i in range(max(map(len, lists), default=0)):
        for lst in lists:
            if i < len(lst):
                out.append(lst[i])
    return out


def build_pulse() -> dict:
    results, errors = {}, {}
    for name, fn in (("hackernews", _hackernews), ("github", _github), ("news", _news)):
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = []
            errors[name] = f"{type(e).__name__}: {e}"[:120]
    pulse = {
        "fetched_at": time.time(),
        "items": _interleave(results["hackernews"], results["github"], results["news"]),
        "errors": errors,
    }
    PULSE_PATH.write_text(json.dumps(pulse, ensure_ascii=False, indent=1))
    return pulse


def get_pulse(max_age_s: int = TTL_S) -> dict:
    if PULSE_PATH.exists():
        cached = json.loads(PULSE_PATH.read_text())
        if time.time() - cached.get("fetched_at", 0) < max_age_s and cached.get("items"):
            return cached
    try:
        return build_pulse()
    except Exception:
        if PULSE_PATH.exists():  # stale beats nothing
            return json.loads(PULSE_PATH.read_text())
        raise


if __name__ == "__main__":
    p = build_pulse()
    print(f"{len(p['items'])} items  errors={p['errors'] or 'none'}")
    for it in p["items"]:
        eng = f"{it['score']}pts·{it['comments']}c" if it["score"] is not None else "—"
        print(f"  [{it['tag']:>16}] {eng:>12}  {it['title'][:80]}")

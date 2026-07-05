"""Thumbnail review + per-video packaging analysis (cached vision, one call/video).

review_thumbnail: draft vs winners (interactive upload).
analyze_packaging: static mqdefault per creator video — reused by production_kit.
"""

import json

from openai import AsyncOpenAI, OpenAI

from . import cache
from .config import EXTRACT_MODEL, LLM_API_KEY
from .corpus import load_corpus

_llm = AsyncOpenAI(api_key=LLM_API_KEY)
_sync_client: OpenAI | None = None

_PACKAGING_SYSTEM = """You analyze a YouTube thumbnail for packaging attributes.
Return JSON only:
{
  "face_present": true/false,
  "face_placement": "left|center|right|close-up|none",
  "expression": "neutral|surprised|thoughtful|smiling|vulnerable|intense",
  "overlay_text_words": 0-5,
  "overlay_sample": "exact visible overlay text or empty string",
  "contrast_direction": "subject bright on dark bg|subject dark on light bg|high saturation|muted",
  "composition": "face + text split|face dominant|text dominant|object focus|minimal",
  "curiosity_gap": "high|medium|low"
}
Describe only what you see — no generic advice."""

_SYSTEM = """You are a YouTube thumbnail strategist. You get: a creator's DRAFT thumbnail,
then reference thumbnails — first the creator's own top-converting videos, then trending
outliers in their niche. Judge the draft against what demonstrably works for this audience.

Return JSON:
{
  "score": 0-100,
  "verdict": one blunt sentence,
  "works": [2-3 specific things the draft does right],
  "fix": [2-4 concrete, actionable changes ranked by impact — composition, text load,
          contrast, emotion, curiosity gap],
  "vs_your_winners": one sentence — what the creator's own top thumbnails do that the draft
                     doesn't (or does),
  "vs_outliers": one sentence — what's working in the niche right now that's relevant
}
Be specific to what you SEE. No generic advice."""


def _thumb_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def analyze_packaging(video: dict) -> dict:
    """Vision-analyzed packaging attrs for one published thumbnail — cached."""
    vid = video["video_id"]
    hit = cache.get("packaging", vid)
    if hit is not None:
        return hit

    global _sync_client
    if _sync_client is None:
        _sync_client = OpenAI(api_key=LLM_API_KEY)

    content = [
        {"type": "text", "text": f"TITLE: {video.get('title', '')[:120]}"},
        {"type": "image_url", "image_url": {"url": _thumb_url(vid), "detail": "low"}},
    ]
    try:
        resp = _sync_client.chat.completions.create(
            model=EXTRACT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _PACKAGING_SYSTEM},
                {"role": "user", "content": content},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        data = {
            "face_present": True,
            "face_placement": "center",
            "expression": "thoughtful",
            "overlay_text_words": 0,
            "overlay_sample": "",
            "contrast_direction": "subject bright on dark bg",
            "composition": "face dominant",
            "curiosity_gap": "medium",
            "_fallback": str(e)[:80],
        }

    data["video_id"] = vid
    data["title"] = video.get("title", "")
    return cache.put("packaging", vid, data)


def top_ctr_videos(
    analytics_rows: list[dict],
    *,
    is_short: bool | None = None,
    n: int = 3,
) -> list[dict]:
    rows = analytics_rows
    if is_short is not None:
        rows = [r for r in rows if r.get("is_short") == is_short]
    rows = [r for r in rows if (r.get("ctr") or 0) > 0]
    return sorted(rows, key=lambda r: -(r.get("ctr") or 0))[:n]


async def review_thumbnail(image_data_url: str) -> dict:
    corpus = load_corpus()
    mine = sorted(corpus["live"], key=lambda v: -v["views"])[:3]
    outliers = sorted(
        (v for vs in corpus["trends"].values() for v in vs),
        key=lambda v: -v["views"],
    )[:3]

    content: list[dict] = [
        {"type": "text", "text": "DRAFT thumbnail to review:"},
        {"type": "image_url", "image_url": {"url": image_data_url, "detail": "low"}},
        {"type": "text", "text": "The creator's top-converting thumbnails:"},
    ]
    for v in mine:
        content.append({"type": "image_url",
                        "image_url": {"url": _thumb_url(v["video_id"]), "detail": "low"}})
    content.append({"type": "text", "text": "Trending outliers in the niche right now:"})
    for v in outliers:
        content.append({"type": "image_url",
                        "image_url": {"url": _thumb_url(v["video_id"]), "detail": "low"}})

    resp = await _llm.chat.completions.create(
        model=EXTRACT_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": content}],
    )
    review = json.loads(resp.choices[0].message.content)

    def _flat(items) -> list[str]:  # model sometimes returns {impact, suggestion} objects
        out = []
        for it in items or []:
            if isinstance(it, dict):
                text = it.get("suggestion") or it.get("point") or json.dumps(it)
                impact = it.get("impact")
                out.append(f"{text}" + (f" ({impact} impact)" if impact else ""))
            else:
                out.append(str(it))
        return out

    review["works"] = _flat(review.get("works"))
    review["fix"] = _flat(review.get("fix"))
    review["references"] = {
        "yours": [{"video_id": v["video_id"], "title": v["title"], "views": v["views"]}
                  for v in mine],
        "outliers": [{"video_id": v["video_id"], "title": v["title"], "views": v["views"],
                      "channel": v["channel_title"]} for v in outliers],
    }
    return review

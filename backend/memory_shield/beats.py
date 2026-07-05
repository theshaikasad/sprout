"""Transcript beat segmentation — one cached gpt-4o-mini call per video.

Segments each video into intro/context/story/demo/sponsor/cta/outro beats with
approximate start/end seconds (estimated from word positions × duration).
"""

import json
import re

from openai import OpenAI

from . import cache
from .config import BEAT_TYPES, EXTRACT_MODEL, LLM_API_KEY

_SYSTEM = f"""You segment a YouTube video transcript into structural beats.
Return JSON: {{"beats": [{{"type": one of {BEAT_TYPES}, "start_pct": 0-100, "end_pct": 0-100, "summary": "one line"}}]}}
Rules:
- Beats must cover the full video (first starts at 0, last ends at 100).
- No overlapping beats; order chronologically.
- Shorts often have only intro + story + outro.
- Skip sponsor if none detected.
Return ONLY the JSON object."""

_client = None


def _estimate_seconds(beats: list[dict], duration_seconds: int) -> list[dict]:
    """Convert percentage ranges to approximate second timestamps."""
    out = []
    for b in beats:
        start = int(duration_seconds * b["start_pct"] / 100)
        end = int(duration_seconds * b["end_pct"] / 100)
        out.append({
            "type": b["type"],
            "start_sec": start,
            "end_sec": max(start + 1, end),
            "summary": b.get("summary", ""),
        })
    return out


def segment_beats(video: dict, transcript: str | None) -> list[dict]:
    """-> [{type, start_sec, end_sec, summary}, ...]"""
    vid = video["video_id"]
    duration = video.get("duration_seconds") or 0
    hit = cache.get("beats", vid)
    if hit is not None:
        return hit

    if not transcript or duration <= 0:
        # Minimal fallback: single story beat
        fallback = [{"type": "story", "start_sec": 0, "end_sec": max(duration, 1), "summary": video["title"][:80]}]
        return cache.put("beats", vid, fallback)

    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY)

    # Cap transcript length for the segmentation call
    text = transcript[:8000]
    user = f"TITLE: {video['title']}\nDURATION_SECONDS: {duration}\nIS_SHORT: {video.get('is_short', False)}\nTRANSCRIPT:\n{text}"
    resp = _client.chat.completions.create(
        model=EXTRACT_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
    )
    raw = json.loads(resp.choices[0].message.content).get("beats", [])
    cleaned = []
    for b in raw:
        btype = b.get("type")
        if btype not in BEAT_TYPES:
            continue
        try:
            start_pct = max(0, min(100, float(b.get("start_pct", 0))))
            end_pct = max(start_pct, min(100, float(b.get("end_pct", start_pct + 10))))
        except (TypeError, ValueError):
            continue
        cleaned.append({"type": btype, "start_pct": start_pct, "end_pct": end_pct, "summary": (b.get("summary") or "")[:120]})
    if not cleaned:
        cleaned = [{"type": "story", "start_pct": 0, "end_pct": 100, "summary": video["title"][:80]}]
    return cache.put("beats", vid, _estimate_seconds(cleaned, duration))

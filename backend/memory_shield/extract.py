"""Per-video extraction: format + topics + hook in ONE cached gpt-4o-mini call.

Spec §6 step 3 budgets one cheap LLM call per video for the format tag; the same
call also returns topics and the hook, so Lane A can write deterministic
Video→Topic/Hook edges (protects the Day-2 killer query from extraction
nondeterminism). Same cost, more skeleton.
"""

import json

from openai import OpenAI

from . import cache
from .config import EXTRACT_MODEL, FORMATS, HOOK_STYLES, LLM_API_KEY

_SYSTEM = f"""You label YouTube videos for a slow-living / self-improvement vlogger's knowledge graph.
Given a video's title, description, and the opening of its transcript, return JSON:
{{
  "format": one of {FORMATS},
  "topics": 1-4 short topic labels (2-4 words each, lowercase, niche-specific,
            e.g. "slow living", "digital detox", "vulnerable storytelling" — NOT generic like "vlog"),
  "hook": {{"text": the opening line that hooks the viewer (from the transcript's
           first sentences; if no transcript, infer a plausible one from the title),
           "style": one of {HOOK_STYLES}}}
}}
Return ONLY the JSON object."""

_client = None


def extract_video(video: dict, transcript: str | None) -> dict:
    """-> {"format": str, "topics": [str], "hook": {"text": str, "style": str}}"""
    hit = cache.get("extract", video["video_id"])
    if hit is not None and not (transcript and not hit.get("_had_transcript")):
        return hit  # recompute only when a transcript newly became available

    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY)

    user = (
        f"TITLE: {video['title']}\n"
        f"DESCRIPTION: {video['description'][:500]}\n"
        f"TRANSCRIPT OPENING: {(transcript or '')[:500] or '(no transcript)'}"
    )
    resp = _client.chat.completions.create(
        model=EXTRACT_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
    )
    data = json.loads(resp.choices[0].message.content)

    # Clamp to enums/shape so the graph stays clean even if the model drifts.
    if data.get("format") not in FORMATS:
        data["format"] = "talking-head"
    hook = data.get("hook") or {}
    data["hook"] = {
        "text": (hook.get("text") or "").strip() or video["title"],
        "style": hook.get("style") if hook.get("style") in HOOK_STYLES else "question",
    }
    data["topics"] = [t.strip().lower() for t in data.get("topics", []) if t and t.strip()][:4]
    data["_had_transcript"] = bool(transcript)
    return cache.put("extract", video["video_id"], data)

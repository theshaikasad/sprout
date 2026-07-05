"""Thumbnail review — your draft vs. what actually converts.

One gpt-4o-mini vision call: the candidate image against the creator's
top-converting thumbnails and the niche's trending outliers (all public
i.ytimg.com URLs — no storage, no CV pipeline). Spec §2's no-CV rule is
amended by the user: this is a single bounded call, not frame analysis.
"""

import json

from openai import AsyncOpenAI

from .config import EXTRACT_MODEL, LLM_API_KEY
from .corpus import load_corpus

_llm = AsyncOpenAI(api_key=LLM_API_KEY)

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

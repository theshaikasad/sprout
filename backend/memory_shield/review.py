"""Idea review — the memory pushes back (recall, inverted).

The creator pitches what THEY want to make; the same graph machinery that
drafts concepts now audits one: evidence for, evidence against, collisions
with competitors/trends, and a recommended treatment — all cited.
"""

import json

from openai import AsyncOpenAI

from .config import EXTRACT_MODEL, LLM_API_KEY, NODE_SET_TRENDS
from .kg import Graph
from .recall import _hook_style_stats, build_bridge, topic_distances

_llm = AsyncOpenAI(api_key=LLM_API_KEY)

_REVIEW_SYSTEM = """You are a content strategist's memory, reviewing an idea the creator pitched.
You get RETRIEVED FACTS from their knowledge graph: their own videos on related topics (views +
ratio vs channel median), conversion stats by hook style, competitor videos on those topics, and
trending videos in the niche.

Return JSON:
{
  "verdict": "make it" | "make it, with changes" | "risky" | "skip",
  "confidence": 0-100,
  "fit": 2-3 sentences — does this fit what converts for THIS creator? Be direct, cite numbers.
  "evidence_for": [{"point": one sentence with a number, "video_id": id}],
  "evidence_against": [{"point": one sentence with a number, "video_id": id}],
  "collisions": [{"point": "who already made this + how to differentiate", "video_id": id}],
  "recommended": {"title": sharper title for the idea, "hook": {"text": opening line, "style":
                  "question|pattern-interrupt|stat|story"}, "format": format from the facts},
  "cited_video_ids": [every video_id used above]
}

HARD RULES: every video_id must appear in the facts; every number must belong to a cited video.
If the creator's history contradicts the idea, say so plainly — a memory that only flatters is
useless. If evidence is thin, lower confidence and say why."""


async def review_idea(idea: str) -> dict:
    g = await Graph.load()
    dists = await topic_distances(idea)
    bridge = build_bridge(g, dists)
    median = g.my_median_views() or 1.0

    my_videos, comp_videos, trend_videos = {}, {}, {}
    for t in bridge:
        for v in t["my_video_ids"]:
            card = g.video_card(v)
            card["ratio"] = round((card["views"] or 0) / median, 2)
            card["related_topic"] = t["label"]
            my_videos[v] = card
        for v in t["comp_video_ids"]:
            card = g.video_card(v)
            card["related_topic"] = t["label"]
            comp_videos[v] = card
        for v in g.videos_covering(t["topic_id"], NODE_SET_TRENDS):
            card = g.video_card(v)
            card["related_topic"] = t["label"]
            trend_videos[v] = card

    facts = {
        "pitched_idea": idea,
        "creator_median_views": median,
        "my_hook_style_conversion": _hook_style_stats(g, median),
        "my_related_videos": sorted(my_videos.values(), key=lambda v: -(v["views"] or 0))[:8],
        "competitor_videos": sorted(comp_videos.values(), key=lambda v: -(v["views"] or 0))[:6],
        "trending_videos": sorted(trend_videos.values(), key=lambda v: -(v["views"] or 0))[:6],
    }

    resp = await _llm.chat.completions.create(
        model=EXTRACT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _REVIEW_SYSTEM},
            {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
        ],
    )
    review = json.loads(resp.choices[0].message.content)

    # anti-slop: strip citations that weren't retrieved
    allowed = {**my_videos, **comp_videos, **trend_videos}
    by_vid = {v["video_id"]: v for v in allowed.values()}
    for key in ("evidence_for", "evidence_against", "collisions"):
        review[key] = [e for e in review.get(key, []) if e.get("video_id") in by_vid]
    review["cited_video_ids"] = [v for v in review.get("cited_video_ids", []) if v in by_vid]
    review["citations"] = [
        {k: by_vid[v].get(k) for k in ("video_id", "title", "channel", "views", "published")}
        for v in review["cited_video_ids"]
    ]
    review["trace"] = {
        "trend": None,
        "topics": [t["topic_id"] for t in bridge[:6]],
        "videos": [by_vid[v]["node_id"] for v in review["cited_video_ids"]],
        "formats": sorted({by_vid[v]["format_node_id"] for v in review["cited_video_ids"]
                           if by_vid[v].get("format_node_id")}),
        "hooks": [],
    }
    return review

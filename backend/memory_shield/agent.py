"""Sprout agent — context pack, tool-fire rules, frontier chat model.

Read tools fire when a fact is needed; write tools only on explicit command.
No number may be stated that didn't come from a tool.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from .analytics_fixture import load_analytics
from .config import CHAT_MODEL, DIGEST_PATH, EXTRACT_MODEL, LLM_API_KEY, NODE_SET_MY_CHANNEL
from .fingerprint import load_fingerprint
from .lifecycle import capture_seed_from_turn, list_drafts, list_seeds, save_idea
from .recall import suggest

_client = AsyncOpenAI(api_key=LLM_API_KEY)

SYSTEM = """You are Sprout — a calm, encouraging creator companion with a memory of one YouTube creator.
You help them create more and consume less. You never bombast, never guilt-trip, never open with stats anxiety.

RULES:
1. You may NOT state any number (views, CTR, retention, ratios, n=) unless it came from a tool result this turn.
2. Read tools when you need a fact; write tools only on explicit user command or confirmed proposal.
3. Destructive actions (forget, delete) always confirm first.
4. Frame weaknesses as "you already won X; here's the next unlock."
5. Every claim about performance must cite a pattern or video from tool output.
6. React, don't compose — offer yes/no/tweak, not blank slates.
7. Use garden language: seeds, planted, sprouted, composted, tending the garden.

You have a context pack each turn with preferences, board state, and digest. Use it naturally."""


def _build_context_pack() -> dict:
    from .preferences import get_preferences

    fp = load_fingerprint()
    analytics = load_analytics()
    seeds = list_seeds()
    planted = [d for d in list_drafts("planted")]
    sprouted = list_drafts("sprouted")[-5:]

    digest = {}
    if DIGEST_PATH.exists():
        try:
            digest = json.loads(DIGEST_PATH.read_text())
        except Exception:
            pass

    return {
        "genre": fp.get("genre", {}),
        "baselines": analytics.get("baselines", {}),
        "seeds_count": len(seeds),
        "seeds_preview": [s["title"] for s in seeds[:4]],
        "planted": [{"title": d["title"], "angle": d.get("angle", "")} for d in planted[:6]],
        "recent_sprouted": [d["title"] for d in sprouted],
        "digest": digest,
        "preferences": get_preferences(),
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_performance",
            "description": "Precomputed PatternNodes + analytics for the creator's channel.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_suggestions",
            "description": "Killer query: cited concept cards for a trend.",
            "parameters": {
                "type": "object",
                "properties": {"trend": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_drafts",
            "description": "Vision board: planted ideas waiting.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_seeds",
            "description": "Seed tray: auto-captured passing mentions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_idea",
            "description": "Save or plant an idea on the vision board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "angle": {"type": "string"},
                    "format_name": {"type": "string"},
                    "state": {"type": "string", "enum": ["seed", "planted"]},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_competitors",
            "description": "True competitor set with outlier-ranked videos.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_trends",
            "description": "Velocity trend radar for the niche.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_pattern",
            "description": "User confirms a pattern hypothesis — strengthen via improve().",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern_label": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["pattern_label", "confirmed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_trend",
            "description": "Decay a trend from memory (confirm with user first).",
            "parameters": {
                "type": "object",
                "properties": {"trend_label": {"type": "string"}},
                "required": ["trend_label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_discourse",
            "description": "What the creator's corner of the internet (Reddit + HN) is talking about, ranked by fit to their fingerprint.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_competitor",
            "description": "Stop tracking a competitor — removes them now AND writes a durable exclusion so they're never re-added (confirm with user first, this is destructive).",
            "parameters": {
                "type": "object",
                "properties": {"handle": {"type": "string"}},
                "required": ["handle"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_preference",
            "description": "Set a durable preference: interruption_budget (low|normal|high), tone, or goals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "enum": ["interruption_budget", "tone", "goals"]},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
]


from .kg import Graph

async def _dispatch_tool(name: str, args: dict) -> Any:
    from .analyzer import run_pattern_scan
    from .corpus import load_corpus
    from .ops import forget_trend, improve

    if name == "get_my_performance":
        patterns = run_pattern_scan(load_corpus()["live"])
        analytics = load_analytics()
        return {
            "patterns": patterns[:12],
            "baselines": analytics.get("baselines", {}),
            "sample_videos": list(analytics.get("per_video", {}).values())[:5],
        }
    if name == "recall_suggestions":
        return await suggest(args.get("trend"))
    if name == "get_drafts":
        return list_drafts("planted")
    if name == "get_seeds":
        return list_seeds()
    if name == "save_idea":
        return save_idea(
            args["title"],
            angle=args.get("angle", ""),
            format_name=args.get("format_name", ""),
            state=args.get("state", "seed"),
        )
    if name == "check_competitors":
        from .preferences import get_preferences
        excluded = set(get_preferences().get("competitor_exclusions", []))
        return [c for c in load_fingerprint().get("competitors", []) if c.get("handle") not in excluded]
    if name == "scan_trends":
        from .cognee_env import cognee  # noqa: F401
        g = await Graph.load()
        from .recall import topic_distances, build_bridge, is_trend_evidence
        from .config import NICHE
        dists_niche = await topic_distances(NICHE)
        waves = []
        for nid, p in sorted(
            (await Graph.load()).by_type("Trend"),
            key=lambda np: np[1].get("peaked_at", ""),
            reverse=True,
        ):
            label = p.get("label") or ""
            dists = await topic_distances(label)
            bridge = build_bridge(g, dists)
            evidence = []
            for v in g.out_rel(nid, "evidenced_by"):
                if is_trend_evidence(g, v, label, dists, dists_niche):
                    card = g.video_card(v)
                    evidence.append(card)
            evidence.sort(key=lambda v: -(v.get("views") or 0))
            waves.append({"label": label, "evidence": evidence[:6]})
        return waves
    if name == "confirm_pattern":
        # Resolve the label to its real PatternNode, then reweight the exact
        # Topic/Format/Hook nodes its evidence videos carry — the human
        # supplies causality, improve() strengthens (confirm) or buries
        # (deny) precisely the trace behind THIS pattern, never a blanket bump.
        label = args.get("pattern_label", "")
        confirmed = bool(args.get("confirmed"))
        g = await Graph.load()
        pattern_id = next(
            (nid for nid, p in g.by_type("PatternNode") if (p.get("label") or "").lower() == label.lower()),
            None,
        )
        if pattern_id is None:
            return {"pattern": label, "confirmed": confirmed, "error": "no matching pattern in memory"}
        evidence_vids = g.props[pattern_id].get("evidence_video_ids", [])
        topics, formats, hooks = set(), set(), set()
        for vid_str in evidence_vids:
            nid = next((n for n, p in g.by_type("Video") if p.get("video_id") == vid_str), None)
            if not nid:
                continue
            topics.update(g.out_rel(nid, "covers"))
            formats.update(g.out_rel(nid, "has_format"))
            hooks.update(g.out_rel(nid, "uses"))
        trace = {"topics": [pattern_id, *topics], "formats": list(formats), "hooks": list(hooks)}
        new_weights = await improve(trace, 25 if confirmed else -25)
        return {"pattern": label, "confirmed": confirmed, "reweighted_nodes": len(new_weights)}
    if name == "forget_trend":
        return await forget_trend(args["trend_label"])
    if name == "search_discourse":
        from .discourse import get_discourse
        return await get_discourse()
    if name == "remove_competitor":
        from .preferences import set_preference
        handle = args["handle"]
        prefs = await set_preference("competitor_exclusions", handle)
        return {"removed": handle, "exclusions": prefs["competitor_exclusions"]}
    if name == "set_preference":
        from .preferences import set_preference
        return await set_preference(args["key"], args["value"])
    return {"error": f"unknown tool {name}"}


async def chat(message: str, history: list[dict] | None = None) -> dict:
    history = history or []
    ctx = _build_context_pack()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "system", "content": f"Context pack:\n{json.dumps(ctx, ensure_ascii=False)}"},
        *history[-8:],
        {"role": "user", "content": message},
    ]

    tool_calls_log = []
    for _ in range(4):
        resp = await _client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            reply = msg.content or ""
            capture_seed_from_turn(message, reply)
            return {"reply": reply, "tool_calls": tool_calls_log}

        messages.append(msg)
        for tc in msg.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            result = await _dispatch_tool(fn, args)
            tool_calls_log.append({"tool": fn, "args": args})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False, default=str)[:12000],
            })

    return {"reply": "I hit my tool limit — try a simpler ask?", "tool_calls": tool_calls_log}

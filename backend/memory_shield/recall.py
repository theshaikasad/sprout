"""The killer query (spec §3) — `recall` in the four-op story.

Orchestrated multi-step retrieval, NOT one search() call:

  Trend node ──(vector similarity over embedded Topic labels)──> my Topics
      └─> my Videos on those Topics ──> best-converting Format   [graph hops]
      + trend evidence videos + competitor Videos on those Topics
  ──> gpt-4o-mini synthesizes N concept cards, each CITING retrieved nodes only.

Returns cards + the literal node path per card (drives the §9.3 graph highlight).

CLI check: python -m memory_shield.recall "LLM agents"
"""

import asyncio
import json
import re
import sys
import time
from statistics import mean

from openai import AsyncOpenAI

from .cognee_env import cognee  # noqa: F401
from cognee.infrastructure.databases.vector import get_vector_engine
from cognee.infrastructure.databases.graph import get_graph_engine

from .config import (
    EXTRACT_MODEL,
    LLM_API_KEY,
    NICHE,
    NODE_SET_COMPETITORS,
    NODE_SET_MY_CHANNEL,
    NODE_SET_TRENDS,
)
from .corpus import load_corpus
from .analytics_fixture import load_analytics
from .analyzer import run_pattern_scan
from .fingerprint import load_fingerprint, load_cold_start
from .cold_start import patterns_enabled, TIER_ESTABLISHED
from .kg import Graph
from .cache import get as cache_get, put as cache_put

BRIDGE_TOP_K = 30
BRIDGE_MAX_DISTANCE = 0.55   # drop weak semantic matches — the bridge must stay honest
EVIDENCE_MAX_DISTANCE = 0.60  # a trend video must be topically near the trend to be cited
NICHE_MAX_DISTANCE = 0.55     # trend outliers must also sit in the creator's niche

_llm = AsyncOpenAI(api_key=LLM_API_KEY)

_SYNTH_SYSTEM = """You are Sprout, a calm encouraging companion for a slow-living / self-improvement YouTuber.
You get RETRIEVED FACTS from a knowledge graph: validated patterns (with n and effect size),
a current trend with trending evidence videos, the creator's genre fingerprint, their real
videos on related topics (views + ratio vs recency-weighted baseline), competitor videos ranked
by outlier score, and hook/format conversion stats.

Produce {n} distinct video concepts as JSON: {{"cards": [...]}}. Each card:
{{
  "title": concrete, specific, clickable — name the actual thing (tool, number, mistake, result).
           NEVER vague futurism ("The Future of X", "How X is Changing Everything"),
  "title_variants": [2 alternates taking DIFFERENT emotional angles than the title —
                     e.g. curiosity gap vs. outcome/number vs. mistake/warning],
  "angle": one sentence naming the SPECIFIC gap or twist: what the trending/competitor videos are
           doing vs. what this creator's proven treatment adds ("they cover X broadly; you convert
           when you build it hands-on"),
  "hook": {{"text": opening line for the first 3 seconds, "style": "question|pattern-interrupt|stat|story"}}
          — prefer the creator's best-converting hook styles per my_hook_style_conversion,
  "format": a format name that appears in the retrieved facts (prefer best_converting_format
            of the topic the card builds on),
  "outline": [3-5 beats, concrete — name the examples/tools/steps, not "introduction ... conclusion"],
  "why": 2-3 sentences of FALSIFIABLE justification with numbers from the facts: cite validated
         patterns (e.g. "2.1× CTR, n=5") AND at least one creator video AND one external signal.
  "topic_labels_used": [topic labels from the facts this card builds on],
  "cited_video_ids": [video_id values that justify this card — MUST include at least one creator
                      video AND at least one trending-now/competitor video],
  "broll_keywords": [3-4 short stock-footage search phrases matching the outline beats,
                     e.g. "server room close up", "developer typing terminal"],
  "thumbnail": {{"concept": ONE concrete visual composition — subject, layout, emotion — that fits
                this creator's format (e.g. "your face right, shocked; terminal with red error left"),
                "overlay_text": 2-4 punchy words max}}
}}

HARD RULES: stay inside the creator's niche and audience — if a trending video targets a different
audience (e.g. game developers when this creator teaches AI/ML engineers), you may use it as
evidence that the trend is big, but never point the card's direction at that other audience.
Every cited_video_id must appear in the facts. Every number in "why" must belong to a
video in cited_video_ids — never quote a view count from a video you did not cite. Write a NEW hook
line (never copy a transcript opening verbatim) and make its text actually match its style. Never
invent videos, numbers, formats, or channels. The trend supplies the angle; the creator's history
supplies the treatment. The three cards must take genuinely different angles (not three rewordings).
already_published_titles is the creator's existing catalog: NEVER propose a concept that repeats one
of those videos (same core subject + same treatment = a repeat, even reworded). Published videos are
PROOF of what converts — every card must be a video the channel does not have yet."""

_SYNTH_SYSTEM_COLD = """You are Sprout, a calm encouraging companion for a YouTube creator who is just getting started.
They do NOT have enough upload history for validated performance patterns yet — do NOT cite n= counts,
CTR multiples, or "your pattern" claims. Ground every card in TRENDING evidence and competitor videos
from the retrieved facts only.

Produce {n} distinct video concepts as JSON: {{"cards": [...]}}. Each card uses the same schema as usual
(title, title_variants, angle, hook, format, outline, why, topic_labels_used, cited_video_ids,
broll_keywords, thumbnail).

COLD-START RULES:
- "why" must cite trending/competitor videos only — honest about not knowing their personal patterns yet.
  Example tone: "Three channels in your niche posted this angle this week and it's moving fast; here's
  a version only you would make because you said you cover {niche}."
- cited_video_ids MUST include at least one trending or competitor video from the facts. Creator videos
  are optional (they may have very few).
- Do NOT invent performance ratios or pattern labels. No "2.1× CTR" unless it appears in facts.
- Stay inside the declared niche. Cards should feel like a warm nudge to post, not a stats lecture.
- The three cards must take genuinely different angles."""


async def topic_distances(trend_label: str) -> dict[str, float]:
    """The semantic hop: topic_id -> distance to the trend text. ONE vector search
    feeds both the bridge (which topics of mine/competitors' relate) and the
    evidence filter (is a trending video actually about this trend)."""
    now = time.monotonic()
    cached = _topic_dist_cache.get(trend_label)
    if cached is not None and (now - cached[1]) < _TOPIC_DIST_TTL:
        return cached[0]

    from .cognee_context import with_user_cognee

    async with with_user_cognee():
        engine = get_vector_engine()
        hits = await engine.search("Topic_label", query_text=trend_label, limit=BRIDGE_TOP_K)
        result = {str(h.id): h.score for h in hits}
        _topic_dist_cache[trend_label] = (result, now)
        return result


_topic_dist_cache: dict[str, tuple[dict[str, float], float]] = {}
_TOPIC_DIST_TTL = 30  # seconds


def build_bridge(g: Graph, dists: dict[str, float]) -> list[dict]:
    """Strong topic hits that the creator OR a competitor has videos on — my
    topics drive the cards, competitor-covered topics supply external evidence
    (exact-label overlap across channels is rare by design)."""
    out = []
    for tid, dist in sorted(dists.items(), key=lambda kv: kv[1]):
        if dist > BRIDGE_MAX_DISTANCE or tid not in g.props:
            continue
        my_vids = g.videos_covering(tid, NODE_SET_MY_CHANNEL)
        comp_vids = g.videos_covering(tid, NODE_SET_COMPETITORS)
        if not my_vids and not comp_vids:
            continue
        fw = g.props[tid].get("feedback_weight") or 0.0
        out.append({
            "topic_id": tid,
            "label": g.props[tid].get("label"),
            "distance": round(dist, 3),
            "feedback_weight": fw,          # improve() bumps this — visible re-rank
            "rank_score": dist - 0.15 * fw,  # lower = better
            "my_video_ids": my_vids,
            "comp_video_ids": comp_vids,
        })
    out.sort(key=lambda t: t["rank_score"])
    return out


# The demand/gap finder (spec §Research tools #4): a graph ANTI-join, not a
# similarity ranking. `covers` is the only edge Cognee actually persists between
# a Video and a Topic — there's no stored Topic-Topic "semantic" edge in this
# schema (semantic adjacency lives in the vector index, queried live via
# topic_distances()). So the set-difference below runs as literal Cypher against
# Kuzu — NOT EXISTS a `my_channel` Video covering this Topic — and the "near your
# fingerprint" filter is applied *after*, in Python, using the same embedding
# space the bridge above uses. This + the bridge's topic-distance search are the
# two places a plain vector search() cannot express the query: the bridge needs
# a live graph hop, this needs a live existential negation over a stored edge.
GAP_FINDER_QUERY_DESC = (
    "Python graph anti-join: Topic in trends/competitors node_set "
    "with NO my_channel Video --covers--> Topic"
)


async def gap_finder(niche_text: str | None = None, top_k: int = 8) -> dict:
    """Trending/competitor Topics with NO `my_channel` Video covering them yet.
    Postgres graph has no raw Cypher — uses in-memory Graph traversal instead."""
    g = await Graph.load()

    candidates = []
    for tid, props in g.props.items():
        if props.get("type") != "Topic":
            continue
        sets = props.get("belongs_to_set") or []
        if not (NODE_SET_TRENDS in sets or NODE_SET_COMPETITORS in sets):
            continue
        if g.videos_covering(tid, NODE_SET_MY_CHANNEL):
            continue
        candidates.append({
            "topic_id": tid,
            "label": props.get("label"),
            "belongs_to_set": sets,
        })

    dists = await topic_distances(niche_text or NICHE)
    for c in candidates:
        c["distance_to_niche"] = round(dists.get(c["topic_id"], 9.9), 3)
    gaps = [c for c in candidates if c["distance_to_niche"] <= BRIDGE_MAX_DISTANCE]
    gaps.sort(key=lambda c: c["distance_to_niche"])

    return {
        "cypher_query": GAP_FINDER_QUERY_DESC,
        "query_mode": "python_anti_join",
        "raw_match_count": len(candidates),
        "gaps": gaps[:top_k],
    }


def _hook_style_stats(g: Graph, median: float) -> dict:
    """Channel-wide conversion by hook style — grounds 'your audience responds to X'."""
    stats: dict[str, list[float]] = {}
    for vid, p in g.by_type("Video"):
        if NODE_SET_MY_CHANNEL not in (p.get("belongs_to_set") or []):
            continue
        hook = next(iter(g.out_rel(vid, "uses")), None)
        style = g.props.get(hook, {}).get("style") if hook else None
        if style:
            stats.setdefault(style, []).append(p.get("views", 0) / median)
    return {
        s: {"videos": len(r), "avg_ratio_vs_median": round(mean(r), 2)}
        for s, r in sorted(stats.items(), key=lambda kv: -mean(kv[1]))
    }


def _recency_baseline(is_short: bool = False) -> float:
    try:
        a = load_analytics()
        key = "short_form_views" if is_short else "long_form_views"
        return float(a.get("baselines", {}).get(key) or 1)
    except Exception:
        return 1.0


def gather_facts(
    g: Graph,
    trend_id: str,
    topics: list[dict],
    dists: dict[str, float],
    dists_niche: dict[str, float],
    *,
    cold_start: bool = False,
) -> dict:
    """Graph hops from bridged topics: my videos + conversion, competitor evidence."""
    median = g.my_median_views() or _recency_baseline(False)
    trend_p = g.props[trend_id]
    trend_label = trend_p.get("label", "")

    try:
        corpus = load_corpus()
        patterns = run_pattern_scan(corpus["live"])
        fingerprint = load_fingerprint()
        analytics = load_analytics()
    except Exception:
        patterns, fingerprint, analytics = [], {}, {}

    per_video = analytics.get("per_video", {})

    trend_evidence = [
        g.video_card(v) for v in g.out_rel(trend_id, "evidenced_by")
        if is_trend_evidence(g, v, trend_label, dists, dists_niche)
    ]

    my_topics = []
    comp_evidence: dict[str, dict] = {}
    for t in topics:
        for cv in t["comp_video_ids"]:
            card = g.video_card(cv)
            card["related_topic"] = t["label"]
            av = per_video.get(card["video_id"], {})
            card["outlier_score"] = av.get("ratio_vs_baseline") or round(card["views"] / max(median, 1), 2)
            comp_evidence[cv] = card
        if not t["my_video_ids"] or len(my_topics) >= 8:
            continue
        vids = [g.video_card(v) for v in t["my_video_ids"]]
        for v in vids:
            av = per_video.get(v["video_id"], {})
            v["ratio"] = av.get("ratio_vs_baseline") or round(v["views"] / median, 2)
            v["ctr"] = av.get("ctr")
            v["avg_view_percentage"] = av.get("avg_view_percentage")
        vids.sort(key=lambda v: -v["views"])
        by_fmt: dict[str, list[float]] = {}
        for v in vids:
            if v["format"]:
                fmt_fw = (g.props.get(v["format_node_id"], {}) or {}).get("feedback_weight") or 0.0
                by_fmt.setdefault(v["format"], []).append(v["ratio"] * (1 + fmt_fw))
        best_format = max(by_fmt.items(), key=lambda kv: mean(kv[1]))[0] if by_fmt else None
        my_topics.append({
            "label": t["label"],
            "semantic_distance_to_trend": t["distance"],
            "feedback_weight": t["feedback_weight"],
            "best_converting_format": best_format,
            "my_videos": vids[:5],
        })

    validated = [p for p in patterns if p.get("confidence") in ("validated", "strong")]
    if cold_start:
        validated = []

    facts = {
        "cold_start": cold_start,
        "trend": {"label": trend_p.get("label"), "peaked_at": trend_p.get("peaked_at")},
        "creator_baseline_views": median,
        "baselines": analytics.get("baselines", {}),
        "genre_fingerprint": fingerprint.get("genre", {}),
        "validated_patterns": validated[:10],
        "my_hook_style_conversion": {} if cold_start else _hook_style_stats(g, median),
        "trending_now_evidence": trend_evidence,
        "my_related_topics": my_topics,
        "competitor_videos_on_related_topics": sorted(
            comp_evidence.values(), key=lambda v: -(v.get("outlier_score") or 0)
        )[:6],
    }
    if cold_start:
        facts["declared_niche"] = fingerprint.get("cold_start", {}).get("niche_query", "")
    return facts


def _allowed_ids(facts: dict) -> dict[str, dict]:
    vids = {}
    for v in facts["trending_now_evidence"]:
        vids[v["video_id"]] = v
    for v in facts["competitor_videos_on_related_topics"]:
        vids[v["video_id"]] = v
    for t in facts["my_related_topics"]:
        for v in t["my_videos"]:
            vids[v["video_id"]] = v
    return vids


_STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "for", "and", "or", "your", "you", "how",
    "with", "on", "i", "my", "is", "what", "why", "vs", "using", "build", "building",
}

# Clickbait patterns the synthesis prompt forbids but the model still emits sometimes.
_SLOP_RE = re.compile(
    r"(?i)\b("
    r"secrets?\s+to|essential\s+guide|supercharg|unlock(ing)?\s+\d|the\s+ultimate|"
    r"mastering\s+|everything\s+you\s+need|future\s+of\s+\w|changing\s+everything|"
    r"5\s+steps\s+to|top\s+5\s+mistakes"
    r")\b"
)


def _title_tokens(title: str) -> set[str]:
    return {
        w for w in re.sub(r"[^a-z0-9 ]", " ", title.lower()).split()
        if w not in _STOPWORDS
    }


def topic_words(labels: list[str]) -> set[str]:
    """Topic-label tokens with naive stemming (agents → agent) for backtest alignment."""
    words: set[str] = set()
    for label in labels:
        for w in _title_tokens(label):
            words.add(w)
            if w.endswith("s") and len(w) > 4:
                words.add(w[:-1])
    return words


def duplicates_published(title: str, published_titles: list[str]) -> str | None:
    """The re-suggestion guard: a card whose title token-overlaps an already
    published video ≥0.5 Jaccard is a repeat, not a suggestion."""
    t = _title_tokens(title)
    for p in published_titles:
        pt = _title_tokens(p)
        if t and pt and len(t & pt) / len(t | pt) >= 0.5:
            return p
    return None


def video_topics_near(g: Graph, vid: str, dists: dict[str, float], max_dist: float) -> bool:
    """True when at least one covered Topic is semantically near the query text."""
    topics = g.out_rel(vid, "covers")
    if not topics:
        return False
    return any(dists.get(t, 9.9) <= max_dist for t in topics)


def title_supports_trend(title: str, trend_label: str) -> bool:
    """YouTube keyword search is noisy — short trends need a title signal too."""
    title_l = title.lower()
    words = [w for w in trend_label.lower().split() if len(w) > 2]
    if len(words) >= 2:
        return sum(1 for w in words if w in title_l) >= max(1, len(words) - 1)
    token = trend_label.strip().lower()
    if len(token) <= 6:
        return bool(re.search(rf"\b{re.escape(token)}\b", title_l))
    return token in title_l


def is_trend_evidence(
    g: Graph,
    vid: str,
    trend_label: str,
    dists_trend: dict[str, float],
    dists_niche: dict[str, float],
) -> bool:
    """Outlier strip / citations: topic graph match + niche + title guard."""
    if not video_topics_near(g, vid, dists_trend, EVIDENCE_MAX_DISTANCE):
        return False
    if not video_topics_near(g, vid, dists_niche, NICHE_MAX_DISTANCE):
        return False
    title = (g.props.get(vid) or {}).get("title") or ""
    return title_supports_trend(title, trend_label)


def _allowed_vocab(facts: dict) -> set[str]:
    """Words/names that may appear in a title — everything else is suspect."""
    vocab: set[str] = set()
    for v in _allowed_ids(facts).values():
        vocab.update(_title_tokens(v.get("title", "")))
        vocab.update(m.lower() for m in re.findall(r"[A-Za-z]+\d+", v.get("title", "")))
    trend = (facts.get("trend") or {}).get("label", "")
    vocab.update(_title_tokens(trend))
    return vocab


def _card_is_slop(card: dict, facts: dict) -> str | None:
    """Return drop-reason if the card fails quality gates, else None."""
    title = card.get("title", "")
    if _SLOP_RE.search(title):
        return "generic clickbait title"
    if duplicates_published(title, facts.get("already_published_titles", [])):
        return "repeat of published video"
    # Invented product names (Gemma4, Fable 5) not present in any cited video/trend.
    vocab = _allowed_vocab(facts)
    for token in re.findall(r"[A-Za-z]+\d+", title):
        if token.lower() not in vocab and not any(token.lower() in v for v in vocab):
            return f"invented name {token!r}"
    cited = [v for v in card.get("cited_video_ids", []) if v in _allowed_ids(facts)]
    cold = facts.get("cold_start")
    min_citations = 1 if cold else 2
    if len(cited) < min_citations:
        return "needs creator + external citation" if not cold else "needs at least one trend/competitor citation"
    allowed = _allowed_ids(facts)
    if not _why_numbers_valid(card.get("why", ""), card, allowed):
        return "why cites numbers not in retrieved videos"
    return None


def _extract_view_counts(text: str) -> list[int]:
    """Pull plausible view-count integers from prose (≥500 to skip ratios like 3.0)."""
    out: list[int] = []
    for m in re.findall(r"\b[\d]{1,3}(?:,\d{3})+\b|\b\d{3,}\b", text):
        n = int(m.replace(",", ""))
        if n >= 500:
            out.append(n)
    return out


def _why_numbers_valid(why: str, card: dict, allowed: dict) -> bool:
    """Every large number in why must match a cited video's views (±5%)."""
    cited_views = [
        allowed[v]["views"]
        for v in card.get("cited_video_ids", [])
        if v in allowed and allowed[v].get("views")
    ]
    if not cited_views:
        return True
    for n in _extract_view_counts(why):
        if not any(abs(n - v) <= max(v * 0.05, 50) for v in cited_views):
            return False
    return True


def build_trace(g: Graph, trend_id: str, card: dict, facts: dict) -> dict:
    """The literal node path behind one card — what the graph panel lights up."""
    bridge_by_label = {t["label"]: t["topic_id"] for t in facts["_bridge"]}
    topic_ids, video_nodes, format_ids, hook_ids = [], [], set(), set()
    allowed = _allowed_ids(facts)
    for lbl in card.get("topic_labels_used", []):
        if lbl in bridge_by_label:
            topic_ids.append(bridge_by_label[lbl])
    for vid in card.get("cited_video_ids", []):
        v = allowed.get(vid)
        if v:
            video_nodes.append(v["node_id"])
            if v.get("format_node_id"):
                format_ids.add(v["format_node_id"])
            if v.get("hook_node_id"):
                hook_ids.add(v["hook_node_id"])
    if not topic_ids:  # fallback: topic hop via the cited videos' covers edges
        bridged = set(bridge_by_label.values())
        for vn in video_nodes:
            topic_ids.extend(t for t in g.out_rel(vn, "covers") if t in bridged)
        topic_ids = list(dict.fromkeys(topic_ids))
    return {
        "trend": trend_id,
        "topics": topic_ids,
        "videos": video_nodes,
        "formats": sorted(format_ids),
        "hooks": sorted(hook_ids),
    }


async def suggest(trend_label: str | None = None, n_cards: int = 3) -> dict:
    cs = load_cold_start()
    tier = cs.get("tier", TIER_ESTABLISHED)
    cold = not patterns_enabled(tier)
    niche_query = cs.get("niche_query") or NICHE

    cache_key = f"v3|{tier}|{(trend_label or '__this_week__').strip().lower()}"
    cached = cache_get("suggest", cache_key)
    if cached:
        return cached

    g = await Graph.load()

    trends = {p.get("label"): nid for nid, p in g.by_type("Trend")}
    if trend_label:
        q = trend_label.strip().lower()
        matches = [
            (lbl, nid) for lbl, nid in trends.items()
            if q == lbl.lower() or q in lbl.lower() or lbl.lower() in q
        ]
        if len(matches) != 1:
            raise ValueError(f"unknown trend {trend_label!r}; have {sorted(trends)}")
        picked = matches
    else:  # "this week": most recent trend first
        picked = sorted(
            trends.items(),
            key=lambda kv: g.props[kv[1]].get("peaked_at", ""),
            reverse=True,
        )[:1]

    label, trend_id = picked[0]
    dists = await topic_distances(label)
    dists_niche = await topic_distances(niche_query)
    bridge = build_bridge(g, dists)
    if not bridge and cold:
        # Cold start: widen bridge to competitor-only topics near the niche
        bridge = []
        for tid, dist in sorted(dists.items(), key=lambda kv: kv[1]):
            if dist > BRIDGE_MAX_DISTANCE or tid not in g.props:
                continue
            comp_vids = g.videos_covering(tid, NODE_SET_COMPETITORS)
            if comp_vids:
                bridge.append({
                    "topic_id": tid,
                    "label": g.props[tid].get("label"),
                    "distance": round(dist, 3),
                    "feedback_weight": 0.0,
                    "rank_score": dist,
                    "my_video_ids": [],
                    "comp_video_ids": comp_vids,
                })
        bridge.sort(key=lambda t: t["rank_score"])
    if not bridge:
        return {"error": f"no semantic bridge from trend {label!r} into your topics"}

    facts = gather_facts(g, trend_id, bridge, dists, dists_niche, cold_start=cold)
    facts["_bridge"] = bridge  # keep topic ids for the trace

    # LIVE catalog only: the memory is blind to the holdout, so it cannot (and
    # must not) avoid holdout titles — re-inventing one is the backtest's win.
    try:
        published_titles = [v["title"] for v in load_corpus()["live"]]
    except Exception:
        published_titles = []
    facts["already_published_titles"] = published_titles

    public_facts = {k: v for k, v in facts.items() if not k.startswith("_")}

    synth = _SYNTH_SYSTEM_COLD if cold else _SYNTH_SYSTEM
    if cold:
        synth = synth.replace("{niche}", niche_query)

    kept: list[dict] = []
    # The anti-slop gate can drop every candidate in one unlucky sample (LLM
    # forgets a second citation) — retry with more spares rather than ever
    # showing an empty result live. Never relax the gate itself.
    for attempt, spares in enumerate((1, 3)):
        resp = await _llm.chat.completions.create(
            model=EXTRACT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": synth.replace("{n}", str(n_cards + spares))},
                {"role": "user", "content": json.dumps(public_facts, ensure_ascii=False)},
            ],
        )
        cards = json.loads(resp.choices[0].message.content).get("cards", [])
        for card in cards:
            reason = _card_is_slop(card, facts)
            if reason:
                print(f"recall: dropped card — {reason}: {card.get('title', '')!r}")
            else:
                kept.append(card)
        if len(kept) >= n_cards:
            break
        if attempt == 0:
            print(f"recall: only {len(kept)}/{n_cards} cards survived — retrying with more spares")
    cards = kept[:n_cards]

    allowed = _allowed_ids(facts)
    for card in cards:  # anti-slop: citations must be retrieved nodes, or they're gone
        card["cited_video_ids"] = [v for v in card.get("cited_video_ids", []) if v in allowed]
        card["citations"] = [
            {k: allowed[v][k] for k in ("video_id", "title", "channel", "views", "published")}
            for v in card["cited_video_ids"]
        ]
        card["trace"] = build_trace(g, trend_id, card, facts)

    result = {"trend": label, "cards": cards, "facts": public_facts, "cold_start": cold}
    if cards:  # never cache a transient LLM miss — it would serve empty forever
        cache_put("suggest", cache_key, result)
    return result


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "--gaps":
        result = asyncio.run(gap_finder())
    else:
        result = asyncio.run(suggest(arg))
    print(json.dumps(result, indent=2, ensure_ascii=False))

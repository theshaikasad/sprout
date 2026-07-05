"""Pattern analyzer — pandas over the analytics table → PatternNodes.

All arithmetic in Python; LLM never estimates numbers. Patterns stratified by
is_short with n + effect size + confidence tiering.

Run: python -m memory_shield.analyzer
"""

from __future__ import annotations

import asyncio
import json
import uuid
from statistics import mean

import pandas as pd

from .analytics_fixture import load_analytics_table
from .config import PATTERN_EARLY_SIGNAL, PATTERN_MIN_SUPPORT
from .cognee_env import cognee  # noqa: F401
from cognee.low_level import setup
from cognee.tasks.storage import add_data_points

from .graph_models import PatternNode, Video

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "memory-shield-patterns")


def _id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"{kind}:{key}")


def _confidence(n: int, effect: float) -> str:
    if n >= PATTERN_MIN_SUPPORT and effect >= 1.5:
        return "strong"
    if n >= PATTERN_MIN_SUPPORT:
        return "validated"
    if n >= PATTERN_EARLY_SIGNAL:
        return "early_signal"
    return "insufficient"


def _compute_patterns(df: pd.DataFrame, is_short: bool) -> list[dict]:
    """Group by feature dimensions; compute effect size vs cohort baseline."""
    cohort = df[df["is_short"] == is_short]
    if cohort.empty:
        return []

    baseline_ctr = cohort["ctr"].median()
    baseline_ret = cohort["avg_view_percentage"].median()
    baseline_subs = cohort["subs_gained"].median() or 1
    baseline_growth = cohort["growth_score"].median() or 1

    patterns: list[dict] = []

    def add_group(kind: str, col: str, metric: str, baseline: float):
        if col not in cohort.columns:
            return
        for val, grp in cohort.groupby(col):
            if not val or len(grp) < PATTERN_EARLY_SIGNAL:
                continue
            n = len(grp)
            if metric == "ctr":
                effect = grp["ctr"].mean() / max(baseline_ctr, 0.001)
            elif metric == "retention":
                effect = grp["avg_view_percentage"].mean() / max(baseline_ret, 1)
            elif metric == "subs_gained":
                effect = grp["subs_gained"].mean() / max(baseline_subs, 1)
            else:
                effect = grp["growth_score"].mean() / max(baseline_growth, 1)
            conf = _confidence(n, effect)
            if conf == "insufficient":
                continue
            label = f"{val} ({effect:.1f}× {metric.replace('_', ' ')}, n={n})"
            patterns.append({
                "kind": kind,
                "label": label,
                "is_short": is_short,
                "support_n": n,
                "effect_size": round(effect, 2),
                "metric": metric,
                "confidence": conf,
                "evidence_video_ids": grp["video_id"].tolist(),
                "feature_value": str(val),
            })

    add_group("Format", "format", "growth_score", baseline_growth)
    add_group("Hook", "hook_style", "ctr", baseline_ctr)
    add_group("Hook", "hook_style", "retention", baseline_ret)

    # Topic patterns — explode topics
    topic_rows = []
    for _, row in cohort.iterrows():
        for t in row.get("topics") or []:
            topic_rows.append({**row.to_dict(), "topic": t})
    if topic_rows:
        tdf = pd.DataFrame(topic_rows)
        for val, grp in tdf.groupby("topic"):
            n = len(grp)
            if n < PATTERN_EARLY_SIGNAL:
                continue
            effect = grp["growth_score"].mean() / max(baseline_growth, 1)
            conf = _confidence(n, effect)
            if conf == "insufficient":
                continue
            patterns.append({
                "kind": "Topic",
                "label": f"{val} ({effect:.1f}× growth, n={n})",
                "is_short": is_short,
                "support_n": n,
                "effect_size": round(effect, 2),
                "metric": "growth_score",
                "confidence": conf,
                "evidence_video_ids": grp["video_id"].tolist(),
                "feature_value": str(val),
            })

    # Title pattern: number in title → CTR
    cohort = cohort.copy()
    cohort["has_number"] = cohort["title"].str.contains(r"\d", regex=True)
    for val, grp in cohort.groupby("has_number"):
        n = len(grp)
        if n < PATTERN_EARLY_SIGNAL:
            continue
        effect = grp["ctr"].mean() / max(baseline_ctr, 0.001)
        conf = _confidence(n, effect)
        if conf == "insufficient":
            continue
        name = "number in title" if val else "no number in title"
        patterns.append({
            "kind": "Packaging",
            "label": f"{name} ({effect:.1f}× CTR, n={n})",
            "is_short": is_short,
            "support_n": n,
            "effect_size": round(effect, 2),
            "metric": "ctr",
            "confidence": conf,
            "evidence_video_ids": grp["video_id"].tolist(),
            "feature_value": name,
        })

    # Pacing: intro-heavy videos (from beats) bleed retention
    intro_bleed_ids = []
    for _, row in cohort.iterrows():
        beats = row.get("beats") or []
        if not beats:
            continue
        intro = next((b for b in beats if b.get("type") == "intro"), None)
        if intro and intro.get("end_sec", 0) > 40:
            intro_bleed_ids.append(row["video_id"])
    if len(intro_bleed_ids) >= PATTERN_EARLY_SIGNAL:
        bleed_grp = cohort[cohort["video_id"].isin(intro_bleed_ids)]
        rest = cohort[~cohort["video_id"].isin(intro_bleed_ids)]
        if not rest.empty:
            effect = rest["avg_view_percentage"].mean() / max(bleed_grp["avg_view_percentage"].mean(), 1)
            patterns.append({
                "kind": "Pacing",
                "label": f"intro >40s bleeds retention ({effect:.1f}× vs short intros, n={len(intro_bleed_ids)})",
                "is_short": is_short,
                "support_n": len(intro_bleed_ids),
                "effect_size": round(effect, 2),
                "metric": "retention",
                "confidence": _confidence(len(intro_bleed_ids), effect),
                "evidence_video_ids": intro_bleed_ids,
                "feature_value": "long_intro",
            })

    return sorted(patterns, key=lambda p: (-p["effect_size"], -p["support_n"]))


def run_pattern_scan(corpus_videos: list[dict] | None = None) -> list[dict]:
    """Compute patterns from analytics table; optionally merge beats from corpus."""
    table = load_analytics_table()
    df = pd.DataFrame(table)

    if corpus_videos:
        beats_map = {v["video_id"]: v.get("beats", []) for v in corpus_videos}
        df["beats"] = df["video_id"].map(lambda vid: beats_map.get(vid, []))

    all_patterns = _compute_patterns(df, is_short=False) + _compute_patterns(df, is_short=True)
    return all_patterns


def patterns_to_data_points(patterns: list[dict]) -> list[PatternNode]:
    points = []
    for p in patterns:
        key = f"{p['kind']}|{p['is_short']}|{p['feature_value']}|{p['metric']}"
        points.append(PatternNode(
            id=_id("pattern", key),
            kind=p["kind"],
            label=p["label"],
            is_short=p["is_short"],
            support_n=p["support_n"],
            effect_size=p["effect_size"],
            metric=p["metric"],
            confidence=p["confidence"],
            evidence_video_ids=p["evidence_video_ids"],
            belongs_to_set=["my_channel"],
        ))
    return points


async def write_patterns_to_graph(patterns: list[dict], corpus_live: list[dict]) -> int:
    """Write PatternNodes + Video-exhibits edges to Cognee."""
    await setup()
    pattern_nodes = patterns_to_data_points(patterns)
    vid_map = {v["video_id"]: v for v in corpus_live}

    # Build exhibits edges on Video nodes
    video_nodes: list[Video] = []
    pattern_by_vid: dict[str, list[PatternNode]] = {}
    for pn in pattern_nodes:
        for vid in pn.evidence_video_ids:
            pattern_by_vid.setdefault(vid, []).append(pn)

    from .ingest import _id as ingest_id  # reuse deterministic video ids

    for vid, pns in pattern_by_vid.items():
        if vid not in vid_map:
            continue
        v = vid_map[vid]
        video_nodes.append(Video(
            id=ingest_id("video", vid),
            video_id=vid,
            title=v["title"],
            views=v["views"],
            likes=v["likes"],
            comment_count=v["comments"],
            published=v["published"],
            is_short=v.get("is_short", False),
            duration_seconds=v.get("duration_seconds", 0),
            beats=v.get("beats", []),
            exhibits=pns,
            belongs_to_set=["my_channel"],
        ))

    all_points = pattern_nodes + video_nodes
    if all_points:
        await add_data_points(all_points, embed_triplets=True)
    return len(pattern_nodes)


async def main():
    from .corpus import load_corpus

    corpus = load_corpus()
    patterns = run_pattern_scan(corpus["live"])
    n = await write_patterns_to_graph(patterns, corpus["live"])
    print(f"analyzer: {n} PatternNodes written")
    for p in patterns[:8]:
        print(f"  [{p['confidence']}] {p['label']}")


if __name__ == "__main__":
    asyncio.run(main())

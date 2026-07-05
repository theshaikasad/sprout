"""Two-lane ingestion into cognee (spec §4, §6) — `remember` in the four-op story.

Lane A — add_data_points(): the deterministic typed skeleton (Creator, Video+metrics,
         Format, Topic, Hook, Trend) with real edges. No LLM. The killer query's
         join runs on THIS.
Lane B — add() + cognify(temporal_cognify=True): transcript docs per node_set for
         semantic depth (chat, GRAPH_COMPLETION). Trend docs land in a DATED dataset
         (e.g. trends_2026_W27) so decay is a scoped forget(), per spec §7.

Holdout discipline: corpus["holdout"] is NEVER ingested — the §10b backtest reads
it from .cache/corpus.json at reveal time.

Run: python -m memory_shield.ingest [--fresh] [--skip-lane-b]
"""

import argparse
import asyncio
import uuid
from datetime import date
from pathlib import Path

from .cognee_env import ROOT as _ROOT, cognee

from cognee.low_level import setup
from cognee.tasks.storage import add_data_points

from .config import (
    NICHE,
    NODE_SET_COMPETITORS,
    NODE_SET_MY_CHANNEL,
    NODE_SET_TRENDS,
)
from .corpus import load_corpus
from .graph_models import Creator, Format, Hook, Topic, Trend, Video

GRAPH_HTML = _ROOT / "graph.html"

DS_MY = "my_channel_docs"
DS_COMP = "competitor_docs"

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "memory-shield")


def _id(kind: str, key: str) -> uuid.UUID:
    """Deterministic node id — re-ingest upserts instead of duplicating."""
    return uuid.uuid5(_NS, f"{kind}:{key}")


def trend_dataset_name(today: date | None = None) -> str:
    y, w, _ = (today or date.today()).isocalendar()
    return f"trends_{y}_W{w:02d}"


def build_lane_a(corpus: dict) -> list:
    """Corpus -> one flat list of DataPoints (shared nodes deduped by dict key)."""
    formats: dict[str, Format] = {}
    topics: dict[str, Topic] = {}
    creators: dict[str, Creator] = {}
    points: list = []

    def fmt(name: str) -> Format:
        return formats.setdefault(name, Format(id=_id("format", name), name=name))

    def topic(label: str, node_set: str) -> Topic:
        t = topics.setdefault(label, Topic(id=_id("topic", label), label=label, belongs_to_set=[]))
        if node_set not in t.belongs_to_set:
            t.belongs_to_set.append(node_set)
        return t

    def creator(channel_id: str, name: str, node_set: str, handle: str = "") -> Creator:
        if channel_id not in creators:
            creators[channel_id] = Creator(
                id=_id("creator", channel_id),
                name=name, niche=NICHE, handle=handle, belongs_to_set=[node_set],
            )
        return creators[channel_id]

    def video(v: dict, by: Creator, node_set: str) -> Video:
        hook = Hook(
            id=_id("hook", v["video_id"]),
            text=v["hook"]["text"], style=v["hook"]["style"], belongs_to_set=[node_set],
        )
        vid = Video(
            id=_id("video", v["video_id"]),
            video_id=v["video_id"],
            title=v["title"],
            views=v["views"],
            likes=v["likes"],
            comment_count=v["comments"],
            published=v["published"],
            is_short=v.get("is_short", False),
            duration_seconds=v.get("duration_seconds", 0),
            beats=v.get("beats", []),
            by=by,
            covers=[topic(t, node_set) for t in v["topics"]],
            uses=hook,
            has_format=fmt(v["format"]),
            belongs_to_set=[node_set],
        )
        points.extend([hook, vid])
        return vid

    me = creator(
        corpus["creator"]["channel_id"], corpus["creator"]["title"],
        NODE_SET_MY_CHANNEL, corpus["creator"]["handle"],
    )
    for v in corpus["live"]:  # holdout stays OUT of the graph (spec §6 step 5)
        video(v, me, NODE_SET_MY_CHANNEL)

    for handle, vids in corpus["competitors"].items():
        for v in vids:
            by = creator(v["channel_id"], v["channel_title"], NODE_SET_COMPETITORS, handle)
            video(v, by, NODE_SET_COMPETITORS)

    for kw, vids in corpus["trends"].items():
        evidence = []
        for v in vids:
            by = creator(v["channel_id"], v["channel_title"], NODE_SET_TRENDS)
            evidence.append(video(v, by, NODE_SET_TRENDS))
        points.append(Trend(
            id=_id("trend", kw),
            label=kw,
            kind="topic",
            peaked_at=max((v["published"] for v in vids), default=date.today().isoformat()),
            evidenced_by=evidence,
            belongs_to_set=[NODE_SET_TRENDS],
        ))

    points.extend(formats.values())
    points.extend(topics.values())
    points.extend(creators.values())
    return points


def _doc(v: dict) -> str:
    return (
        f"VIDEO: {v['title']}\n"
        f"CHANNEL: {v['channel_title']}\n"
        f"PUBLISHED: {v['published']}  VIEWS: {v['views']}\n"
        f"TRANSCRIPT:\n{v['transcript'][:6000]}"
    )


async def run_lane_b(corpus: dict) -> list[str]:
    """Transcript docs -> per-node_set datasets -> one cognify pass. Returns dataset names."""
    ds_trends = trend_dataset_name()
    batches = [
        (DS_MY, NODE_SET_MY_CHANNEL, [_doc(v) for v in corpus["live"] if v["transcript"]]),
        (DS_COMP, NODE_SET_COMPETITORS,
         [_doc(v) for vs in corpus["competitors"].values() for v in vs if v["transcript"]]),
        (ds_trends, NODE_SET_TRENDS,
         [_doc(v) for vs in corpus["trends"].values() for v in vs if v["transcript"]]),
    ]
    datasets = []
    for ds, node_set, docs in batches:
        if docs:
            await cognee.add(docs, dataset_name=ds, node_set=[node_set])
            datasets.append(ds)
    if not datasets:  # e.g. transcript backfill still pending — Lane A stands alone
        print("Lane B: no transcript docs available; skipping cognify")
        return []
    await cognee.cognify(datasets=datasets, temporal_cognify=True)
    return datasets


async def main(fresh: bool, skip_lane_b: bool):
    if fresh:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
    await setup()

    corpus = load_corpus()
    points = build_lane_a(corpus)
    print(f"Lane A: {len(points)} data points -> add_data_points()")
    await add_data_points(points, embed_triplets=True)
    print("Lane A done.")

    if not skip_lane_b:
        datasets = await run_lane_b(corpus)
        print(f"Lane B done: cognify over {datasets}")

    await cognee.visualize_graph(str(GRAPH_HTML))
    print(f"Graph written to {GRAPH_HTML}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--fresh", action="store_true", help="prune cognee stores first")
    p.add_argument("--skip-lane-b", action="store_true", help="skeleton only (no LLM)")
    args = p.parse_args()
    asyncio.run(main(args.fresh, args.skip_lane_b))

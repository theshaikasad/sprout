"""improve() and forget() — the write-back half of the four-op story (spec §7).

improve : reported performance bumps `feedback_weight` on the Hook+Format+Topic
          combo behind a card, via the graph engine's NATIVE
          set_node_feedback_weights. recall's ranking reads these weights, so
          the re-rank is visible on the next /suggest — the Memory Shield Effect.
forget  : trend decay. Lane A nodes go via delete_nodes (Trend + its evidence
          Videos + their Hooks); Lane B docs via cognee.forget(dataset=…) on the
          dated trend datasets. Cognee has no auto-TTL — this is the deliberate,
          manually-driven decay the spec calls for.
"""

from .cognee_env import cognee
from cognee.infrastructure.databases.graph import get_graph_engine

from .kg import Graph

MAX_WEIGHT = 5.0
MIN_WEIGHT = -1.0


async def improve(trace: dict, performance_pct: float) -> dict:
    """`trace` is a card's retrieval trace (§3 output). performance_pct is the
    one hand-entered number: views vs channel average, e.g. +40 or -25."""
    from .cognee_context import with_user_cognee

    delta = max(-1.0, min(1.0, performance_pct / 100.0))
    node_ids = list(dict.fromkeys(
        (trace.get("topics") or []) + (trace.get("formats") or []) + (trace.get("hooks") or [])
    ))
    if not node_ids:
        return {}

    async with with_user_cognee():
        engine = await get_graph_engine()
        current = await engine.get_node_feedback_weights(node_ids) or {}
        new_weights = {
            nid: max(MIN_WEIGHT, min(MAX_WEIGHT, float(current.get(nid) or 0.0) + delta))
            for nid in node_ids
        }
        await engine.set_node_feedback_weights(new_weights)
    return new_weights


async def forget_trend(trend_label: str) -> dict:
    """Decay one trend: Lane A subgraph out of the graph, Lane B docs out of
    their dated dataset. Shared Topic nodes are kept — only trend-scoped
    evidence dies."""
    from .cognee_context import with_user_cognee

    deleted_nodes = 0
    deleted_videos = 0
    forgotten_datasets: list[str] = []

    async with with_user_cognee():
        g = await Graph.load()
        trend_id = next(
            (nid for nid, p in g.by_type("Trend") if p.get("label") == trend_label), None
        )
        if trend_id is None:
            raise ValueError(f"unknown trend {trend_label!r}")

        video_ids = g.out_rel(trend_id, "evidenced_by")
        hook_ids = [h for v in video_ids for h in g.out_rel(v, "uses")]
        doomed = [trend_id, *video_ids, *hook_ids]

        engine = await get_graph_engine()
        await engine.delete_nodes(doomed)
        deleted_nodes = len(doomed)
        deleted_videos = len(video_ids)

        try:
            datasets = await cognee.datasets.list_datasets()
            for ds in datasets:
                name = getattr(ds, "name", str(ds))
                if name.startswith("trends_"):
                    await cognee.forget(dataset=name)
                    forgotten_datasets.append(name)
        except Exception:
            pass  # no trend docs in Lane B yet (transcript backfill pending) — Lane A decay stands

    return {
        "trend": trend_label,
        "deleted_nodes": deleted_nodes,
        "deleted_videos": deleted_videos,
        "forgotten_datasets": forgotten_datasets,
    }

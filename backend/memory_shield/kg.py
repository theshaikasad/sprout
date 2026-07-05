"""In-memory snapshot of the cognee graph + traversal helpers.

At demo scale (~2k nodes) one snapshot beats per-hop DB round-trips, and the
traversal trace the UI needs (§9.3 visible path) falls out of the same walk.
"""

from collections import defaultdict

from .cognee_env import cognee  # noqa: F401 — wires stores before engine import

from cognee.infrastructure.databases.graph import get_graph_engine


class Graph:
    def __init__(self, nodes, edges):
        self.props: dict[str, dict] = {str(nid): p for nid, p in nodes}
        self.out: dict[str, list[tuple[str, str]]] = defaultdict(list)  # id -> [(rel, dst)]
        self.inc: dict[str, list[tuple[str, str]]] = defaultdict(list)  # id -> [(rel, src)]
        for src, dst, rel, *_ in edges:
            self.out[str(src)].append((rel, str(dst)))
            self.inc[str(dst)].append((rel, str(src)))

    @classmethod
    async def load(cls) -> "Graph":
        engine = await get_graph_engine()
        nodes, edges = await engine.get_graph_data()
        return cls(nodes, edges)

    # --- traversal ------------------------------------------------------
    def by_type(self, t: str) -> list[tuple[str, dict]]:
        return [(nid, p) for nid, p in self.props.items() if p.get("type") == t]

    def out_rel(self, nid: str, rel: str) -> list[str]:
        return [dst for r, dst in self.out.get(nid, []) if r == rel]

    def in_rel(self, nid: str, rel: str) -> list[str]:
        return [src for r, src in self.inc.get(nid, []) if r == rel]

    def node_sets(self, nid: str) -> list[str]:
        return self.props.get(nid, {}).get("belongs_to_set") or []

    # --- domain shortcuts (the join's hops) -------------------------------
    def videos_covering(self, topic_id: str, node_set: str) -> list[str]:
        return [v for v in self.in_rel(topic_id, "covers") if node_set in self.node_sets(v)]

    def video_card(self, vid: str) -> dict:
        """Everything a citation needs about one Video node."""
        p = self.props[vid]
        fmt = next(iter(self.out_rel(vid, "has_format")), None)
        hook = next(iter(self.out_rel(vid, "uses")), None)
        by = next(iter(self.out_rel(vid, "by")), None)
        return {
            "node_id": vid,
            "video_id": p.get("video_id"),
            "title": p.get("title"),
            "views": p.get("views", 0),
            "published": p.get("published"),
            "channel": self.props.get(by, {}).get("name") if by else None,
            "format": self.props.get(fmt, {}).get("name") if fmt else None,
            "format_node_id": fmt,
            "hook": self.props.get(hook, {}).get("text") if hook else None,
            "hook_style": self.props.get(hook, {}).get("style") if hook else None,
            "hook_node_id": hook,
            "topics": [self.props[t].get("label") for t in self.out_rel(vid, "covers")],
        }

    def my_median_views(self, node_set: str = "my_channel") -> float:
        views = sorted(
            p.get("views", 0) for _, p in self.by_type("Video")
            if node_set in (p.get("belongs_to_set") or [])
        )
        n = len(views)
        return float(views[n // 2]) if n else 0.0

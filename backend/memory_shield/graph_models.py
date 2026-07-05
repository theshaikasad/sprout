"""Cognee custom graph schema (spec §5).

These DataPoint subclasses ARE the graph: each is both a node schema and, via its
relationship fields, an edge schema. The cross-`node_set` join in the killer query
(§3) traverses these edges, so the shapes here are load-bearing.
"""

from typing import Any

from pydantic import SkipValidation

from cognee.low_level import DataPoint


class Creator(DataPoint):
    name: str
    niche: str
    handle: str = ""
    metadata: dict = {"index_fields": ["name", "niche"]}


class Topic(DataPoint):
    label: str
    metadata: dict = {"index_fields": ["label"]}


class Hook(DataPoint):
    text: str
    style: str
    metadata: dict = {"index_fields": ["text", "style"]}


class Format(DataPoint):
    name: str
    metadata: dict = {"index_fields": ["name"]}


class Audio(DataPoint):
    title: str
    metadata: dict = {"index_fields": ["title"]}


class Video(DataPoint):
    video_id: str
    title: str
    views: int
    likes: int
    comment_count: int
    published: str
    is_short: bool = False
    duration_seconds: int = 0
    beats: list[dict] = []  # [{type, start_sec, end_sec, summary}]

    by: SkipValidation[Any] = None
    covers: SkipValidation[Any] = None
    uses: SkipValidation[Any] = None
    has_format: SkipValidation[Any] = None
    set_to: SkipValidation[Any] = None
    exhibits: SkipValidation[Any] = None  # -> list[PatternNode]

    metadata: dict = {"index_fields": ["title"]}


class Trend(DataPoint):
    label: str
    kind: str
    peaked_at: str
    evidenced_by: SkipValidation[Any] = None
    metadata: dict = {"index_fields": ["label"]}


class PatternNode(DataPoint):
    """Precomputed analytics pattern — n + effect size, never LLM-invented."""
    kind: str          # Hook|Format|Topic|Packaging|Audience|Timing|Pacing
    label: str         # human-readable pattern description
    is_short: bool     # stratified by format class
    support_n: int
    effect_size: float # ratio vs baseline (e.g. 2.1 = 2.1× CTR)
    metric: str        # ctr|retention|subs_gained|growth_score
    confidence: str    # early_signal|validated|strong
    evidence_video_ids: list[str] = []
    metadata: dict = {"index_fields": ["label", "kind"]}


class Draft(DataPoint):
    """Vision-board idea: seed | planted | sprouted."""
    title: str
    angle: str = ""
    format_name: str = ""
    state: str = "seed"  # seed | planted | sprouted
    topic_labels: list[str] = []
    concept_art_path: str = ""
    derived_from: SkipValidation[Any] = None
    provenance: str = ""
    created_at: str = ""
    planted_at: str = ""
    sprouted_at: str = ""
    metadata: dict = {"index_fields": ["title", "angle"]}


class Preference(DataPoint):
    """User memory: goals, tone, exclusions, interruption budget."""
    key: str
    value: str
    metadata: dict = {"index_fields": ["key", "value"]}


class CommentTheme(DataPoint):
    label: str
    sentiment: str
    on: SkipValidation[Any] = None
    metadata: dict = {"index_fields": ["label"]}


__all__ = [
    "Creator",
    "Topic",
    "Hook",
    "Format",
    "Audio",
    "Video",
    "Trend",
    "PatternNode",
    "Draft",
    "Preference",
    "CommentTheme",
]

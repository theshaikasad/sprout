"""Cold-start tiers for creators with thin or empty back-catalogs.

Tiers align with PATTERN_MIN_SUPPORT (n=3) and CATALOG_ESTABLISHED_MIN (10):
  empty      — 0 videos; no fingerprint from history; declared niche required
  warming    — 1–9 videos; too few for pattern-level confidence (n<3)
  established — 10+ videos; full pipeline unchanged
"""

from __future__ import annotations

from .config import CATALOG_ESTABLISHED_MIN, NICHE, PATTERN_MIN_SUPPORT

TIER_EMPTY = "empty"
TIER_WARMING = "warming"
TIER_ESTABLISHED = "established"


def classify_tier(live_video_count: int) -> str:
    if live_video_count <= 0:
        return TIER_EMPTY
    if live_video_count < CATALOG_ESTABLISHED_MIN:
        return TIER_WARMING
    return TIER_ESTABLISHED


def patterns_enabled(tier: str) -> bool:
    """Only established catalogs get pattern-confidence-gated suggestions."""
    return tier == TIER_ESTABLISHED


def filter_patterns(patterns: list[dict], tier: str) -> list[dict]:
    if patterns_enabled(tier):
        return patterns
    return []


def niche_text(
    *,
    tier: str,
    declared_niche: str = "",
    genre_label: str = "",
) -> str:
    if declared_niche.strip():
        return declared_niche.strip()
    if tier == TIER_ESTABLISHED and genre_label.strip():
        return genre_label.strip()
    return NICHE


def build_cold_start_meta(
    *,
    tier: str,
    live_video_count: int,
    declared_niche: str = "",
    genre_label: str = "",
) -> dict:
    return {
        "tier": tier,
        "live_video_count": live_video_count,
        "declared_niche": declared_niche.strip(),
        "patterns_enabled": patterns_enabled(tier),
        "pattern_min_support": PATTERN_MIN_SUPPORT,
        "established_at": CATALOG_ESTABLISHED_MIN,
        "niche_query": niche_text(
            tier=tier,
            declared_niche=declared_niche,
            genre_label=genre_label,
        ),
    }


def genre_summary_for_tier(
    *,
    tier: str,
    live_video_count: int,
    declared_niche: str,
    genre_label: str,
    dominant_format: str,
) -> str:
    niche = declared_niche.strip() or genre_label or "your niche"
    fmt = (dominant_format or "your style").replace("-", " ")

    if tier == TIER_EMPTY:
        if declared_niche.strip():
            return (
                f"We don't have any of your videos yet — I can't read your patterns from history. "
                f"You told me this channel is about {declared_niche.strip()}. "
                f"Here's what's converting in that space right now to get you started, "
                f"and this gets sharper every time you post."
            )
        return (
            "We don't have any of your videos yet — I can't find your patterns from history. "
            "Tell me what this channel is about, and I'll pull what's converting in that niche "
            "to get you started. It gets sharper with every upload."
        )

    if tier == TIER_WARMING:
        hint = ""
        if genre_label and live_video_count > 0:
            hint = (
                f" From your {live_video_count} video{'s' if live_video_count != 1 else ''} "
                f"so far, I'm seeing hints of {genre_label} — mostly {fmt} — but that's too few "
                f"for me to trust as a pattern yet."
            )
        return (
            f"I don't have enough of your videos yet to find reliable patterns "
            f"(I need about {PATTERN_MIN_SUPPORT}+ with similar signals, and you have {live_video_count})."
            f"{hint} "
            f"Here's what's converting in {niche} right now to get you started — "
            f"this gets sharper as you post."
        )

    return (
        f"Your last {live_video_count} videos lean toward {genre_label}, "
        f"mostly as {fmt} — and your vulnerable personal essays "
        f"convert best when they're honest and specific. Sound right?"
    )


def needs_declared_niche(tier: str, declared_niche: str = "") -> bool:
    return tier == TIER_EMPTY and not declared_niche.strip()

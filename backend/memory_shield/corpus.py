"""Assemble the demo corpus: fetch + transcripts + extraction + HOLDOUT PARTITION.

Spec §6 step 5: the temporal split is decided HERE, at ingest time. Creator videos
published after HOLDOUT_CUTOFF go to `holdout` (never ingested into the live
graph); the §10b backtest reveal reads them from the saved corpus JSON.

Run: python -m memory_shield.corpus
"""

import json
from datetime import date, timedelta

from .config import (
    CACHE_DIR,
    COMPETITOR_HANDLES,
    COMPETITOR_VIDEO_LIMIT,
    CREATOR_HANDLE,
    CREATOR_VIDEO_LIMIT,
    HOLDOUT_CUTOFF,
    TREND_KEYWORDS,
    TREND_VIDEOS_PER_KEYWORD,
    missing_keys,
)
from .beats import segment_beats
from .extract import extract_video
from .transcripts import get_transcript, reset_circuit
from .youtube import channel_videos, resolve_channel, trend_videos

CORPUS_PATH = CACHE_DIR / "corpus.json"


def _noop(stage: str, detail: str = "") -> None:
    pass


def _enrich(videos: list[dict], progress=_noop, label: str = "") -> list[dict]:
    """Attach transcript + extraction (both cached) to each video dict."""
    for i, v in enumerate(videos):
        progress("enriching", f"{label} · {i + 1}/{len(videos)} · {v['title'][:40]}")
        v["transcript"] = get_transcript(v["video_id"])
        v.update(extract_video(v, v["transcript"]))
        v["beats"] = segment_beats(v, v["transcript"])
    return videos


def holdout_cutoff_for(handle: str) -> str:
    """Lana gets the fixed Apr-1-2026 cutoff (holdout personal essays make the
    backtest reveal sing); any other connected channel gets ~90 days."""
    if handle == CREATOR_HANDLE:
        return HOLDOUT_CUTOFF.isoformat()
    return (date.today() - timedelta(days=90)).isoformat()


def build_corpus(creator_handle: str | None = None, progress=_noop) -> dict:
    if missing := missing_keys():
        raise SystemExit(f"Missing env keys: {missing}")
    handle = creator_handle or CREATOR_HANDLE

    if CORPUS_PATH.exists():
        try:
            cached = json.loads(CORPUS_PATH.read_text())
            if cached.get("creator", {}).get("handle") == handle and cached.get("live"):
                progress("cached", f"reusing {len(cached['live'])}-video corpus for {handle}")
                return cached
        except Exception:
            pass

    reset_circuit()

    progress("fetching", f"resolving {handle}")
    creator = resolve_channel(handle)
    progress("fetching", f"{creator['title']} · pulling uploads")
    mine = _enrich(channel_videos(handle, CREATOR_VIDEO_LIMIT), progress, creator["title"])

    cutoff = holdout_cutoff_for(handle)
    live = [v for v in mine if v["published"] < cutoff]
    holdout = [v for v in mine if v["published"] >= cutoff]

    competitors = {}
    for comp in COMPETITOR_HANDLES:
        try:
            progress("fetching", f"competitor {comp}")
            competitors[comp] = _enrich(
                channel_videos(comp, COMPETITOR_VIDEO_LIMIT), progress, comp
            )
        except Exception as e:  # one bad channel must not sink the corpus
            print(f"WARN: skipping {comp}: {e}")

    trends = {}
    for kw in TREND_KEYWORDS:
        progress("fetching", f"trend search · {kw}")
        trends[kw] = _enrich(trend_videos(kw, TREND_VIDEOS_PER_KEYWORD), progress, kw)

    corpus = {
        "creator": {**creator, "handle": handle},
        "holdout_cutoff": cutoff,
        "live": live,
        "holdout": holdout,
        "competitors": competitors,
        "trends": trends,
    }
    CORPUS_PATH.write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    return corpus


def load_corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text())


if __name__ == "__main__":
    c = build_corpus()
    n_comp = sum(len(v) for v in c["competitors"].values())
    n_trend = sum(len(v) for v in c["trends"].values())
    with_t = sum(
        1 for v in c["live"] + c["holdout"]
        + [x for vs in c["competitors"].values() for x in vs]
        + [x for vs in c["trends"].values() for x in vs]
        if v["transcript"]
    )
    total = len(c["live"]) + len(c["holdout"]) + n_comp + n_trend
    print(f"creator: {c['creator']['title']} ({c['creator']['handle']})")
    print(f"cutoff:  {c['holdout_cutoff']}  ->  live={len(c['live'])}  HOLDOUT={len(c['holdout'])}")
    print(f"competitors: {n_comp} videos across {len(c['competitors'])} channels")
    print(f"trends: {n_trend} videos across {len(c['trends'])} keywords")
    print(f"total: {total} videos, {with_t} with transcripts")

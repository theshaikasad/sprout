"""Reset per-workspace JSON caches when a new channel connects."""

import shutil

from .config import CACHE_DIR, DRAFTS_PATH
from .track import TRACK_PATH

SUGGEST_DIR = CACHE_DIR / "suggest"


def clear_workspace_state() -> None:
    """Drop the vision board, track state, and suggest cache so a reconnect
    starts clean."""
    if DRAFTS_PATH.exists():
        DRAFTS_PATH.unlink()
    if TRACK_PATH.exists():
        TRACK_PATH.unlink()
    if SUGGEST_DIR.exists():
        shutil.rmtree(SUGGEST_DIR)

"""Tiny JSON disk cache (spec §12: never re-pay for the same fetch or LLM call)."""

import json
import re
from typing import Any

from .config import CACHE_DIR


def _path(namespace: str, key: str):
    safe = re.sub(r"[^A-Za-z0-9_@-]+", "_", key)
    d = CACHE_DIR / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def get(namespace: str, key: str) -> Any | None:
    p = _path(namespace, key)
    if p.exists():
        return json.loads(p.read_text())
    return None


def put(namespace: str, key: str, value: Any) -> Any:
    _path(namespace, key).write_text(json.dumps(value, ensure_ascii=False, indent=1))
    return value


def clear_namespace(namespace: str) -> int:
    """Wipe every cached entry in a namespace. Used after improve() — any
    cached `suggest` result may reflect stale feedback_weight, so a reweight
    must invalidate all of it, not just the one trend that was rated."""
    d = CACHE_DIR / namespace
    if not d.exists():
        return 0
    n = 0
    for f in d.glob("*.json"):
        f.unlink()
        n += 1
    return n

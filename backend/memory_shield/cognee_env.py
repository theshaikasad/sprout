"""The one blessed way to import cognee in this project.

With SPROUT_DATABASE_URL set: postgres graph + pgvector via Cloud SQL.
Without: local kuzu/lancedb under .cognee/ (legacy single-tenant dev).
"""

import os
from pathlib import Path

from . import config  # noqa: F401 — env vars BEFORE cognee import

import cognee

ROOT = Path(__file__).resolve().parent.parent

if os.getenv("SPROUT_DATABASE_URL"):
    # Cognee reads DB_* / GRAPH_* / VECTOR_* from environment (set in config.py)
    os.environ.setdefault("DB_HOST", config.DB_HOST)
    os.environ.setdefault("DB_PORT", config.DB_PORT)
    os.environ.setdefault("DB_USERNAME", config.DB_USERNAME)
    os.environ.setdefault("DB_PASSWORD", config.DB_PASSWORD)
    os.environ.setdefault("DB_NAME", config.DB_NAME)
    # Ephemeral per-user file cache still under project root
    cognee.config.data_root_directory(str(ROOT / ".cognee" / "data"))
    cognee.config.system_root_directory(str(ROOT / ".cognee" / "system"))
else:
    cognee.config.data_root_directory(str(ROOT / ".cognee" / "data"))
    cognee.config.system_root_directory(str(ROOT / ".cognee" / "system"))

__all__ = ["cognee", "ROOT"]

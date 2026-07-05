"""Central config: keys, the demo creator, competitors, trend keywords, holdout cutoff.

Everything that decides *what* we ingest lives here so ingestion stays declarative.
"""

import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the REPO root (one level above backend/)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Cognee multi-user + postgres graph when SPROUT_DATABASE_URL is set
_sprout_db_url = os.getenv("SPROUT_DATABASE_URL", "")
if _sprout_db_url:
    os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "true")
    os.environ.setdefault("DB_PROVIDER", "postgres")
    os.environ.setdefault("GRAPH_DATABASE_PROVIDER", "postgres")
    os.environ.setdefault("GRAPH_DATASET_DATABASE_HANDLER", "postgres_graph")
    os.environ.setdefault("VECTOR_DB_PROVIDER", "pgvector")
    os.environ.setdefault("VECTOR_DATASET_DATABASE_HANDLER", "pgvector")
    _pg_host = os.getenv("DB_HOST", "localhost")
    _pg_port = os.getenv("DB_PORT", "5432")
    _pg_user = os.getenv("DB_USERNAME", "postgres")
    _pg_pass = os.getenv("DB_PASSWORD", "postgres")
    for _key, _val in {
        "GRAPH_DATABASE_HOST": _pg_host,
        "GRAPH_DATABASE_PORT": _pg_port,
        "GRAPH_DATABASE_USERNAME": _pg_user,
        "GRAPH_DATABASE_PASSWORD": _pg_pass,
        "VECTOR_DB_HOST": _pg_host,
        "VECTOR_DB_PORT": _pg_port,
        "VECTOR_DB_USERNAME": _pg_user,
        "VECTOR_DB_PASSWORD": _pg_pass,
    }.items():
        os.environ.setdefault(_key, _val)
    if _pg_host.startswith("/cloudsql/"):
        from .cognee_cloudsql import apply_cloudsql_patches

        apply_cloudsql_patches(_pg_host)
else:
    os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

# Spec §12: gpt-4o-mini everywhere (cognee 1.2.2 defaults to gpt-5-mini otherwise).
os.environ.setdefault("LLM_MODEL", "openai/gpt-4o-mini")

# --- Keys -------------------------------------------------------------------
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# --- Caching (spec §12: never re-pay for the same fetch) --------------------
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Postgres app state — sqlite fallback for local dev without Cloud SQL
_db_url = os.getenv("SPROUT_DATABASE_URL", "")
if _db_url:
    SPROUT_DATABASE_URL = _db_url
else:
    SPROUT_DATABASE_URL = f"sqlite:///{CACHE_DIR / 'sprout_app.db'}"
MAX_USERS = int(os.getenv("MAX_USERS", "10"))

# Google OAuth (YouTube + Analytics)
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://api.sprout.asad.codes/auth/youtube/callback",
)

# Cognee relational DB (cognee_meta)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "cognee_meta")

# CORS
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,https://sprout.asad.codes",
    ).split(",")
    if o.strip()
]

# Internal cron secret
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Telegram link HMAC
TELEGRAM_LINK_SECRET = os.getenv("TELEGRAM_LINK_SECRET", "sprout-dev-link-secret")

# --- The demo corpus (keep TIGHT: ~60-80 videos total, spec §6) -------------
CREATOR_HANDLE = os.getenv("CREATOR_HANDLE", "@LanaBlakely")

# Adjacent slow-living / self-improvement vloggers (size band ~0.3×–10× Lana's subs).
COMPETITOR_HANDLES = [
    "@struthless",           # digital doom / self-improvement essays — named fallback
    "@MattDAvella",          # minimalism / intentional living
    "@lavendaire",           # self-care / personal growth
    "@muchelleb",            # intentional living / productivity
    "@TheFinancialDiet",     # life-advice adjacent
    "@PickUpLimes",          # slow living / wellness
]

# Trends = refreshed keyword search (spec §6 step 4), not a magic detector.
TREND_KEYWORDS = [
    "slow living",
    "digital minimalism",
    "morning routine habits",
    "self care routine",
    "intentional living",
]

# --- Corpus limits (spec §6: keep the demo graph tight)
CREATOR_VIDEO_LIMIT = 60        # most recent uploads (pre-partition)
COMPETITOR_VIDEO_LIMIT = 8      # per competitor
TREND_VIDEOS_PER_KEYWORD = 4    # 5 keywords x 4 = ~20 trend videos
TREND_LOOKBACK_DAYS = 14

# --- Extraction (one cached gpt-4o-mini call per video, spec §6 step 3 + §12)
EXTRACT_MODEL = "gpt-4o-mini"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")  # frontier model for user-facing chat
FORMATS = [
    "talking-head",
    "voiceover-broll",
    "vlog",
    "personal-essay",
    "listicle",
    "interview",
    "day-in-life",
]
HOOK_STYLES = ["question", "pattern-interrupt", "stat", "story", "vulnerable-confession"]
BEAT_TYPES = ["intro", "context", "story", "demo", "sponsor", "cta", "outro"]
NICHE = "slow-living and self-improvement vlogging"

# --- node_sets (spec §5) ----------------------------------------------------
NODE_SET_MY_CHANNEL = "my_channel"
NODE_SET_COMPETITORS = "competitors"
NODE_SET_TRENDS = "trends"
NODE_SET_DRAFTS = "drafts"

# --- Temporal holdout (spec §6 step 5) --------------------------------------
# Creator videos published AFTER this cutoff are held out of the live graph and
# revealed in the backtest. FIXED date (not relative): Apr 1 2026 puts Lana's
# vulnerable-essay holdout hits in the reveal window.
HOLDOUT_CUTOFF = date(2026, 4, 1)

# §10b backtest — slow-living trend bridges to her holdout personal essays.
BACKTEST_TREND = "slow living"
DEMO_DEFAULT_TREND = BACKTEST_TREND

# --- Analytics / patterns ---------------------------------------------------
SHORT_MAX_SECONDS = 60          # YouTube Shorts threshold
PATTERN_MIN_SUPPORT = 3         # minimum n for a surfaced pattern
PATTERN_EARLY_SIGNAL = 2        # n=2 tier
CATALOG_ESTABLISHED_MIN = 10    # full fingerprint + pattern pipeline at this count
SEED_COMPOST_DAYS = 21          # unplanted seeds expire after ~3 weeks
RECENCY_HALF_LIFE_DAYS = 180    # trailing baseline decay

# The graph update loop (spec: Cognee does NOT auto-update — we orchestrate).
# In-process background refresh; 0 disables the loop (CLI-only refresh).
REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL_SECONDS", "3600"))

ANALYTICS_PATH = CACHE_DIR / "analytics.json"
ANALYTICS_TABLE_PATH = CACHE_DIR / "analytics_table.json"
FINGERPRINT_PATH = CACHE_DIR / "fingerprint.json"
DRAFTS_PATH = CACHE_DIR / "drafts.json"
DIGEST_PATH = CACHE_DIR / "digest.json"
PREFS_PATH = CACHE_DIR / "preferences.json"

# Concept-art feature flag (cut-line: gradient fallback when off)
CONCEPT_ART_ENABLED = os.getenv("CONCEPT_ART_ENABLED", "false").lower() == "true"


def missing_keys() -> list[str]:
    """Which required keys are absent — used to fail fast before ingestion."""
    missing = []
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not YOUTUBE_API_KEY:
        missing.append("YOUTUBE_API_KEY")
    return missing

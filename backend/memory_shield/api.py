"""FastAPI backend (spec §8) — one service, JSON everywhere.

/chat is deliberately an AGENT over the Cognee memory, not a prompt template:
the model chooses between recall (the killer query) and graph-memory search as
tools. That framing — agent over memory that sharpens — is the pitch.

Run: uvicorn memory_shield.api:app --reload --port 8000
"""

import asyncio
import json
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel

from .auth.deps import optional_user
from .db.context import UserContext
from .cognee_env import cognee
from cognee import SearchType  # after cognee_env: roots/env must be pinned first
from .config import (
    CORS_ORIGINS,
    EXTRACT_MODEL,
    LLM_API_KEY,
    BACKTEST_TREND,
    DEMO_DEFAULT_TREND,
    NICHE,
    TELEGRAM_BOT_TOKEN,
    CRON_SECRET,
)
from .corpus import build_corpus, load_corpus
from .contrast import contrast as run_contrast
from .agent import chat as agent_chat
from .lifecycle import (
    list_drafts,
    list_planted,
    list_seeds,
    list_sprouted,
    save_idea as lifecycle_save,
    update_draft,
    delete_draft,
    plant_idea,
    mark_sprouted,
    compost_stale_seeds,
)
from .fingerprint import build_fingerprint, load_fingerprint
from .analytics_fixture import build_analytics, load_analytics
from .analyzer import run_pattern_scan
from .ingest import main as run_ingest
from .kg import Graph
from .ops import forget_trend, improve
from .pulse import get_pulse
from .recall import (
    suggest,
    gap_finder,
    topic_distances,
    topic_words,
    _title_tokens,
    _STOPWORDS,
    build_bridge,
    is_trend_evidence,
)
from .track import get_track
from .review import review_idea
from .thumbs import review_thumbnail
from .youtube import resolve_channel


async def _scheduled_refresh_loop():
    """Per-user background refresh when postgres multi-user is enabled."""
    from .config import REFRESH_INTERVAL_SECONDS, SPROUT_DATABASE_URL
    from .refresh import run_refresh

    if REFRESH_INTERVAL_SECONDS <= 0:
        return
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        try:
            digests = await run_refresh()
            print(f"scheduled refresh: {digests}", flush=True)
        except Exception as e:
            print(f"scheduled refresh skipped — {e}", flush=True)


async def _bootstrap_demo_memory():
    """Postgres: ensure demo uid has a Cognee dataset and kick ingest if graph is empty."""
    from .config import SPROUT_DATABASE_URL
    from .cognee_context import is_postgres_multi_user, with_user_cognee
    from .db.context import UserContext, set_current_user
    from .db.models import Preference, User
    from .db.sync_session import init_sync_db, sync_session
    from .onboarding import ensure_cognee_user, run_onboarding

    if not is_postgres_multi_user():
        return

    try:
        init_sync_db()
        with sync_session() as session:
            user = session.get(User, "demo")
            if not user:
                user = User(
                    uid="demo",
                    display_name="Demo Creator",
                    is_demo=True,
                    onboarding_status="pending",
                )
                session.add(user)
                session.flush()
                session.add(Preference(uid="demo"))
                session.commit()
                session.refresh(user)

        set_current_user(
            UserContext(
                uid=user.uid,
                is_demo=user.is_demo,
                cognee_user_id=user.cognee_user_id,
                cognee_dataset_id=user.cognee_dataset_id,
                youtube_channel_id=user.youtube_channel_id or "",
                telegram_chat_id=user.telegram_chat_id or "",
            )
        )
        await ensure_cognee_user("demo", "demo@sprout.internal")

        with sync_session() as session:
            user = session.get(User, "demo")
            if user:
                set_current_user(
                    UserContext(
                        uid=user.uid,
                        is_demo=user.is_demo,
                        cognee_user_id=user.cognee_user_id,
                        cognee_dataset_id=user.cognee_dataset_id,
                        youtube_channel_id=user.youtube_channel_id or "",
                        telegram_chat_id=user.telegram_chat_id or "",
                    )
                )

        async with with_user_cognee():
            g = await Graph.load()
            n_trends = len(g.by_type("Trend"))
            if n_trends >= 1:
                print(
                    f"demo graph ready: {len(g.props)} nodes, {n_trends} trends",
                    flush=True,
                )
                return

        print("demo graph empty — starting fixture onboarding ingest", flush=True)
        asyncio.create_task(
            run_onboarding("demo", "demo@sprout.internal", use_real_analytics=False)
        )
    except Exception as e:
        print(f"demo bootstrap failed ({e}) — will retry via /connect", flush=True)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from .db.sync_session import init_sync_db
    from .telegram_bot import poll_forever

    try:
        init_sync_db()
        from .db.schema import ensure_schema
        ensure_schema()
        from .db.session import init_db
        await init_db()
        from .config import SPROUT_DATABASE_URL
        if SPROUT_DATABASE_URL and "postgres" in SPROUT_DATABASE_URL:
            from cognee.infrastructure.databases.relational import create_db_and_tables
            await create_db_and_tables()
    except Exception as e:
        print(f"db init skipped: {e}")

    asyncio.create_task(_bootstrap_demo_memory())

    async def _warm():
        try:
            from .db.context import UserContext, set_current_user
            from .db.models import User
            from .db.sync_session import sync_session

            with sync_session() as session:
                user = session.get(User, "demo")
            if user:
                set_current_user(
                    UserContext(
                        uid=user.uid,
                        is_demo=user.is_demo,
                        cognee_user_id=user.cognee_user_id,
                        cognee_dataset_id=user.cognee_dataset_id,
                        youtube_channel_id=user.youtube_channel_id or "",
                        telegram_chat_id=user.telegram_chat_id or "",
                    )
                )
            await suggest(DEMO_DEFAULT_TREND)
            await backtest_route()
            print("demo cache warmed (suggest + backtest)")
        except Exception as e:
            print(f"demo warmup skipped: {e}")

    asyncio.create_task(_warm())
    asyncio.create_task(_scheduled_refresh_loop())
    if TELEGRAM_BOT_TOKEN:
        asyncio.create_task(poll_forever())
    yield


app = FastAPI(title="Sprout", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)

from .routes_auth import router as auth_router
app.include_router(auth_router)


@app.middleware("http")
async def attach_user_context(request: Request, call_next):
    from .auth.deps import bind_request_user

    try:
        await bind_request_user(request.headers.get("authorization"))
    except Exception:
        pass
    return await call_next(request)

from .concept_art import ART_DIR
app.mount("/concept-art", StaticFiles(directory=str(ART_DIR)), name="concept-art")

_llm = AsyncOpenAI(api_key=LLM_API_KEY)

LANE_A_TYPES = {"Video", "Topic", "Hook", "Format", "Creator", "Trend", "PatternNode", "Draft"}


class FeedbackBody(BaseModel):
    trace: dict
    performance_pct: float


class DecayBody(BaseModel):
    trend: str


class ChatBody(BaseModel):
    message: str
    history: list[dict] = []


def _video_fit(g: Graph, vid: str, bridge: list[dict]) -> str:
    """Strong / stretch / skip — how well this outlier bridges into the creator's topics."""
    bridged = {b["topic_id"]: b["distance"] for b in bridge if b["my_video_ids"]}
    hits = [bridged[t] for t in g.out_rel(vid, "covers") if t in bridged]
    if hits:
        d = min(hits)
    else:
        my_bridge = [b for b in bridge if b["my_video_ids"]]
        if not my_bridge:
            return "skip"
        d = min(b["distance"] for b in my_bridge)
    if d <= 0.38:
        return "strong"
    if d <= 0.50:
        return "stretch"
    return "skip"


async def get_trends_payload():
    return await trends()


@app.get("/fingerprint")
async def fingerprint_route():
    try:
        return load_fingerprint()
    except Exception:
        return build_fingerprint()


@app.get("/patterns")
async def patterns_route():
    from .cold_start import filter_patterns
    from .fingerprint import load_cold_start

    corpus = load_corpus()
    cs = load_cold_start()
    patterns = run_pattern_scan(corpus["live"])
    return {"patterns": filter_patterns(patterns, cs.get("tier", "established"))}


@app.get("/garden")
async def garden_route():
    """Home surface: consistency + waiting ideas + seed tray + full plant library."""
    cad = await cadence_route()
    track = await get_track()
    planted = list_planted()
    seeds = list_seeds()
    sprouted = list_sprouted()
    fp = {}
    try:
        fp = load_fingerprint()
    except Exception:
        pass
    streak_weeks = max(0, 12 - (cad.get("days_since_last") or 0) // 7) if cad.get("days_since_last") is not None else 0

    corpus = load_corpus()
    g = await Graph.load()
    median = g.my_median_views() or 1.0
    plants_by_id: dict[str, dict] = {}
    for v in corpus["live"] + corpus["holdout"]:
        plants_by_id[v["video_id"]] = {
            "video_id": v["video_id"],
            "title": v["title"],
            "published": v["published"],
            "views": v["views"],
            "ratio": round(v["views"] / median, 2),
            "from_idea": False,
            "draft_id": "",
        }
    for d in sprouted:
        vid = d.get("posted_video_id") or ""
        if vid and vid in plants_by_id:
            plants_by_id[vid] = {
                **plants_by_id[vid],
                "from_idea": True,
                "draft_id": d["id"],
                "title": d.get("title") or plants_by_id[vid]["title"],
            }
        elif vid:
            plants_by_id[vid] = {
                "video_id": vid,
                "title": d.get("title") or vid,
                "published": d.get("sprouted_at", "")[:10],
                "views": 0,
                "ratio": 0,
                "from_idea": True,
                "draft_id": d["id"],
            }
    plants = sorted(plants_by_id.values(), key=lambda p: p["published"], reverse=True)

    return {
        "consistency": {
            "days_since_last": cad.get("days_since_last"),
            "median_gap_days": cad.get("median_gap_days"),
            "momentum_weeks": min(streak_weeks, 12),
            "encouragement": track.get("headline") or "Your garden is waiting — got a seed?",
        },
        "planted": planted,
        "seeds": seeds,
        "plants": plants,
        "genre": fp.get("genre", {}),
    }


@app.get("/analytics")
async def analytics_route():
    try:
        return load_analytics()
    except Exception:
        return build_analytics()


@app.get("/trends")
async def trends():
    g = await Graph.load()
    dists_niche = await topic_distances(NICHE)
    out = []
    for nid, p in sorted(
        g.by_type("Trend"), key=lambda np: np[1].get("peaked_at", ""), reverse=True
    ):
        label = p.get("label") or ""
        dists = await topic_distances(label)
        bridge = build_bridge(g, dists)
        evidence = []
        for v in g.out_rel(nid, "evidenced_by"):
            if not is_trend_evidence(g, v, label, dists, dists_niche):
                continue
            card = g.video_card(v)
            fit = _video_fit(g, v, bridge)
            if fit == "skip":
                continue
            evidence.append({**card, "fit": fit})
        evidence.sort(key=lambda v: -(v["views"] or 0))
        out.append({
            "node_id": nid,
            "label": label,
            "peaked_at": p.get("peaked_at"),
            "evidence": len(evidence),
            "evidence_videos": [
                {
                    "video_id": v["video_id"],
                    "title": v["title"],
                    "channel": v["channel"],
                    "views": v["views"],
                    "published": v["published"],
                    "fit": v["fit"],
                }
                for v in evidence[:6]
            ],
        })
    return out


@app.get("/library")
async def library():
    """The ingested corpus as media: creator profile + every video the memory
    holds (and how many are sealed in the holdout). Thumbnails come free from
    i.ytimg.com — the UI is thumbnail-first by design."""
    from .youtube import resolve_channel

    corpus = load_corpus()
    g = await Graph.load()
    median = g.my_median_views() or 1.0

    def slim(v: dict) -> dict:
        return {
            "video_id": v["video_id"],
            "title": v["title"],
            "published": v["published"],
            "views": v["views"],
            "ratio": round(v["views"] / median, 2),
            "format": v.get("format"),
            "topics": v.get("topics", []),
            "channel": v.get("channel_title"),
        }

    creator = {**corpus["creator"], **resolve_channel(corpus["creator"]["handle"])}
    competitors = []
    for handle, vids in corpus["competitors"].items():
        try:
            info = resolve_channel(handle)
        except Exception:
            info = {"title": handle, "avatar": ""}
        competitors.append({
            "handle": handle,
            "title": info.get("title", handle),
            "avatar": info.get("avatar", ""),
            "subscribers": info.get("subscribers", 0),
            "videos": [slim(v) for v in sorted(vids, key=lambda v: -v["views"])],
        })

    return {
        "creator": creator,
        "holdout_cutoff": corpus["holdout_cutoff"],
        "live_videos": [slim(v) for v in sorted(corpus["live"], key=lambda v: v["published"], reverse=True)],
        "holdout_count": len(corpus["holdout"]),
        "competitors": competitors,
        "trend_videos": [
            slim(v) for vs in corpus["trends"].values() for v in vs
        ],
    }


@app.get("/suggest")
async def suggest_route(trend: str | None = None):
    try:
        return await suggest(trend)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        traceback.print_exc()  # transient LLM/store hiccup — log it, try once more
        return await suggest(trend)


@app.get("/gaps")
async def gaps_route(niche: str | None = None):
    """Graph anti-join: trending/competitor Topics with NO my_channel Video
    covering them — real evergreen gaps. Returns the literal Cypher too, for
    the RAG-contrast panel."""
    return await gap_finder(niche)


@app.post("/feedback")
async def feedback_route(body: FeedbackBody):
    new_weights = await improve(body.trace, body.performance_pct)
    # Any cached /suggest result may reflect pre-reweight feedback_weight —
    # bust all of it so the very next call shows the re-rank live, not a
    # byte-identical cached response (this is the "memory gets sharper"
    # centerpiece; a stale cache here would silently break it on stage).
    from .cache import clear_namespace
    cleared = clear_namespace("suggest")
    return {"updated": new_weights, "cache_cleared": cleared, "note": "re-run /suggest to see the re-rank"}


@app.post("/decay")
async def decay_route(body: DecayBody):
    try:
        result = await forget_trend(body.trend)
    except ValueError as e:
        raise HTTPException(404, str(e))
    from .cache import clear_namespace
    clear_namespace("suggest")  # a forgotten trend must not linger in a cached card
    return result


@app.get("/graph")
async def graph_route():
    """Lane A skeleton for the viz panel (Entities/Events would drown it)."""
    g = await Graph.load()
    keep = {nid for nid, p in g.props.items() if p.get("type") in LANE_A_TYPES}
    nodes = [
        {
            "id": nid,
            "type": g.props[nid].get("type"),
            "label": g.props[nid].get("label") or g.props[nid].get("title")
            or g.props[nid].get("name") or g.props[nid].get("text", "")[:40],
            "node_sets": g.props[nid].get("belongs_to_set") or [],
            "views": g.props[nid].get("views"),
            "feedback_weight": g.props[nid].get("feedback_weight") or 0.0,
        }
        for nid in keep
    ]
    edges = [
        {"source": src, "target": dst, "rel": rel}
        for src, targets in g.out.items() if src in keep
        for rel, dst in targets if dst in keep
    ]
    return {"nodes": nodes, "edges": edges}


# --- the workspace: review · ideas board · cadence ---------------------------

class ReviewBody(BaseModel):
    idea: str


class IdeaBody(BaseModel):
    title: str
    source: str = "generated"
    payload: dict = {}
    target: str | None = None


class IdeaPatch(BaseModel):
    status: str | None = None
    target: str | None = None


@app.post("/review")
async def review_route(body: ReviewBody):
    if len(body.idea.strip()) < 8:
        raise HTTPException(422, "pitch needs a few more words")
    try:
        return await review_idea(body.idea.strip())
    except Exception:
        traceback.print_exc()
        return await review_idea(body.idea.strip())


@app.get("/ideas")
async def ideas_route(state: str | None = None):
    return list_drafts(state)


@app.post("/ideas")
async def add_idea_route(body: IdeaBody):
    st = body.payload.get("state", "planted") if body.payload else "planted"
    return lifecycle_save(
        body.title,
        angle=body.payload.get("angle", ""),
        format_name=body.payload.get("format", ""),
        state=st,
        provenance=body.source,
    )


@app.patch("/ideas/{idea_id}")
async def patch_idea_route(idea_id: str, body: IdeaPatch):
    try:
        patch = {}
        if body.status:
            state_map = {"saved": "seed", "scripting": "planted", "filming": "planted", "posted": "sprouted"}
            patch["state"] = state_map.get(body.status, body.status)
        if body.target:
            patch["target"] = body.target
        return update_draft(idea_id, patch)
    except ValueError:
        raise HTTPException(404, "no such idea")


@app.delete("/ideas/{idea_id}")
async def delete_idea_route(idea_id: str):
    delete_draft(idea_id)
    return {"ok": True}


@app.post("/ideas/{idea_id}/plant")
async def plant_route(idea_id: str):
    return plant_idea(idea_id)


@app.get("/ideas/{idea_id}/production-kit")
async def production_kit_route(idea_id: str):
    import uuid as _uuid

    from .db.context import require_uid
    from .db.models import Draft
    from .db.sync_session import sync_session
    from .production_kit import ensure_production_kit

    uid = require_uid()
    with sync_session() as session:
        d = session.get(Draft, _uuid.UUID(idea_id))
        if not d or d.uid != uid:
            raise HTTPException(404, "no such idea")
        if d.state != "planted":
            raise HTTPException(400, "production kit is generated when an idea is planted")
        draft = {
            "id": str(d.id),
            "title": d.title,
            "angle": d.angle,
            "format_name": d.format_name,
            "topic_labels": d.topic_labels or [],
            "state": d.state,
        }
    return ensure_production_kit(draft)


@app.post("/ideas/{idea_id}/sprout")
async def sprout_route(idea_id: str):
    return await mark_sprouted(idea_id)


@app.get("/cadence")
async def cadence_route():
    """The agent's nudge: real posting cadence from real publish dates."""
    from datetime import date
    from statistics import median as med

    corpus = load_corpus()
    dates = sorted(
        date.fromisoformat(v["published"])
        for v in corpus["live"] + corpus["holdout"]
    )
    if len(dates) < 3:
        return {"days_since_last": None}
    gaps = [(b - a).days for a, b in zip(dates[-11:-1], dates[-10:])]
    days_since = (date.today() - dates[-1]).days
    median_gap = round(med(gaps)) if gaps else None
    return {
        "days_since_last": days_since,
        "median_gap_days": median_gap,
        "last_published": dates[-1].isoformat(),
        "overdue": bool(median_gap and days_since > median_gap),
    }



@app.get("/pulse")
async def pulse_route():
    """Discourse radar — Reddit + niche news × fingerprint."""
    from .discourse import get_discourse
    return await get_discourse()


@app.get("/telegram/nudge")
async def telegram_nudge_route():
    from .telegram_bot import get_scripted_nudge
    return {"nudge": get_scripted_nudge()}


@app.post("/telegram/send")
async def telegram_send_route(
    body: dict | None = None,
    ctx: UserContext = Depends(optional_user),
):
    """Push a proactive nudge to the signed-in user's linked Telegram chat."""
    from .nudges import _competitor_anxiety_copy
    from .telegram_bot import chat_id_for_uid, send_nudge_to_user
    from .track import get_track

    payload = body or {}
    text = payload.get("message")
    target_uid = payload.get("uid") or ctx.uid
    chat_id = chat_id_for_uid(target_uid)
    if not text:
        track = await get_track(force=True)
        text = f"🌱 {track.get('headline', '')}"
    if _competitor_anxiety_copy(text):
        raise HTTPException(
            400,
            "competitor-comparison pushes are disabled — use check_competitors in chat (pull-only)",
        )
    sent = send_nudge_to_user(target_uid, text)
    return {
        "sent": sent,
        "text": text,
        "uid": target_uid,
        "chat_id": chat_id or None,
        "configured": bool(TELEGRAM_BOT_TOKEN),
    }


@app.get("/telegram/poll")
async def telegram_poll_route():
    """Long-poll Telegram for new incoming messages, reply live, save any as
    seeds. Call this on an interval from the frontend — no public webhook URL
    needed, which is what makes replies work during a local demo recording."""
    from .telegram_bot import poll_once
    processed = poll_once()
    return {"processed": processed, "configured": bool(TELEGRAM_BOT_TOKEN)}


@app.get("/track")
async def track_route(force: bool = False):
    """Peace of mind, automated: fresh public view counts for the newest
    uploads, judged vs the channel median — and fed straight into improve()
    on each video's Topic/Format nodes. The creator never reports a number."""
    return await get_track(force)


class ThumbBody(BaseModel):
    image_data_url: str  # data:image/...;base64,... from the browser


@app.post("/thumbnail-review")
async def thumbnail_review_route(body: ThumbBody):
    if not body.image_data_url.startswith("data:image/"):
        raise HTTPException(422, "send a data:image/... URL")
    try:
        return await review_thumbnail(body.image_data_url)
    except Exception:
        traceback.print_exc()
        return await review_thumbnail(body.image_data_url)


# --- Legacy demo connect (fixture analytics only) -----------------------------

class ConnectBody(BaseModel):
    handle: str = ""


@app.post("/connect")
async def connect_route(body: ConnectBody):
    """Demo-only fast path — real users use POST /onboarding/start after YouTube OAuth."""
    from .onboarding import get_onboarding_status, run_onboarding
    from .db.context import get_current_user

    ctx = get_current_user()
    if ctx.uid != "demo" and not ctx.is_demo:
        raise HTTPException(400, "use /onboarding/start after YouTube OAuth")
    status = get_onboarding_status("demo")
    if status.get("status") == "building":
        raise HTTPException(409, "already building")
    asyncio.create_task(run_onboarding("demo", "demo@sprout.internal", use_real_analytics=False))
    return {"ok": True, "channel": status.get("channel"), "rebuilding": True}


@app.get("/connect/status")
async def connect_status():
    from .onboarding import get_onboarding_status
    from .db.context import get_current_user

    s = get_onboarding_status(get_current_user().uid)
    return {**s, "stage": s.get("stage", "idle"), "elapsed": 0}


@app.get("/health")
async def health():
    return {"ok": True}


def _check_cron_secret(request: Request) -> None:
    if not CRON_SECRET:
        raise HTTPException(503, "cron not configured")
    if request.headers.get("x-cron-secret") != CRON_SECRET:
        raise HTTPException(401, "invalid cron secret")


@app.post("/internal/cron/refresh")
async def cron_refresh(request: Request):
    _check_cron_secret(request)
    from .refresh import run_refresh

    return {"digests": await run_refresh()}


@app.post("/internal/cron/live-stats")
async def cron_live_stats(request: Request):
    _check_cron_secret(request)
    from sqlmodel import select

    from .db.models import User
    from .db.sync_session import sync_session
    from .live_stats import poll_live_stats

    results = []
    with sync_session() as session:
        users = list(
            session.exec(
                select(User).where(User.onboarding_status == "ready")
            ).all()
        )
    for user in users:
        try:
            deltas = await asyncio.to_thread(poll_live_stats, user.uid)
            results.append({"uid": user.uid, "deltas": deltas})
        except Exception as e:
            results.append({"uid": user.uid, "error": str(e)[:200]})
    return {"results": results}


# Title words too generic to count as alignment (minutes, explained, …).
_WEAK_TITLE = _STOPWORDS | {
    "minutes", "explained", "guide", "tutorial", "complete", "course", "intro",
    "introduction", "build", "built", "make", "video", "videos", "new", "best",
    "top", "key", "own", "real", "world", "weekend", "step", "steps", "easy",
    "simple", "quick", "full", "free", "learn", "learning", "deep", "dive",
}


def _meaningful_title_tokens(title: str) -> set[str]:
    return {w for w in _title_tokens(title) if w not in _WEAK_TITLE}


@app.get("/backtest")
async def backtest_route(trend: str | None = None):
    """§10b temporal-holdout backtest — blind graph vs real holdout reveal."""
    corpus = load_corpus()
    analytics = {}
    try:
        analytics = load_analytics()
        per_video = analytics.get("per_video", {})
    except Exception:
        per_video = {}

    proof_trend = trend or BACKTEST_TREND
    result = await suggest(proof_trend)
    cards = result.get("cards", [])

    reveals = []
    for v in corpus["holdout"]:
        av = per_video.get(v["video_id"], {})
        is_short = v.get("is_short", False)
        baseline_key = "short_form_views" if is_short else "long_form_views"
        baseline = (analytics.get("baselines", {}).get(baseline_key) if per_video else None) or 1
        ratio = av.get("ratio_vs_baseline") or round(v["views"] / max(baseline, 1), 2)
        reveals.append({
            "video_id": v["video_id"],
            "title": v["title"],
            "published": v["published"],
            "views": v["views"],
            "is_short": is_short,
            "ratio_vs_baseline": ratio,
            "topics": v.get("topics", []),
            "format": v.get("format"),
            "hook_style": (v.get("hook") or {}).get("style"),
        })
    reveals.sort(key=lambda r: -r["ratio_vs_baseline"])

    champion = reveals[0] if reveals else None
    trend_words = topic_words([proof_trend])

    matches = []
    for i, c in enumerate(cards):
        card_topics = c.get("topic_labels_used", [])
        card_title_words = _meaningful_title_tokens(c.get("title", ""))
        for r in reveals:
            holdout_topic_words = topic_words(r["topics"])
            holdout_title_words = _meaningful_title_tokens(r["title"])
            topic_ov = topic_words(card_topics) & holdout_topic_words
            title_ov = card_title_words & holdout_title_words
            trend_ov = trend_words & (holdout_topic_words | holdout_title_words)
            if not topic_ov and not trend_ov and len(title_ov) < 2:
                continue
            shared = topic_ov | title_ov | trend_ov
            matches.append({
                "card_index": i,
                "card_title": c.get("title"),
                "holdout_video": r["title"],
                "holdout_video_id": r["video_id"],
                "holdout_views": r["views"],
                "ratio_vs_baseline": r["ratio_vs_baseline"],
                "shared_topics": sorted(shared)[:8],
                "alignment_score": len(topic_ov) * 3 + len(title_ov) + len(trend_ov) * 2,
            })

    best_match = (
        max(matches, key=lambda m: (m["ratio_vs_baseline"], m["alignment_score"]))
        if matches else None
    )

    return {
        "holdout_cutoff": corpus["holdout_cutoff"],
        "proof_trend": proof_trend,
        "champion": champion,
        "best_match": best_match,
        "suggested": result,
        "holdout_reveal": sorted(reveals, key=lambda r: -r["views"]),
        "matches": matches,
    }


@app.get("/contrast")
async def contrast_route(trend: str | None = None):
    """§10a — plain vector RAG vs killer join on the same question."""
    try:
        return await run_contrast(trend)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception:
        traceback.print_exc()
        return await run_contrast(trend)


# --- /chat: the agent that operates the studio -------------------------------

_AGENT_SYSTEM = """You are Memory Shield, a content-strategy agent operating a Cognee knowledge
graph of the creator's channel, competitors, and current trends. You can run the whole studio:
watch how their uploads are really doing, list what's overperforming in the niche, run the recall
join for cited concepts, quote what was actually said in videos (transcript search), audit their
ideas, plan ideas onto their board with a publish date, and decay dead trends out of memory.
Performance feedback is autonomous (public view counts feed improve() directly) — NEVER ask the
creator for their numbers; call channel_watch instead.
Everything you claim must come from a tool result: real titles, real view counts. Answer like a
sharp, concise strategist and cite video titles + views when you rely on them."""

_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recall_suggestions",
            "description": "The killer query: for a trend (or 'this week' if omitted), traverse "
                           "the graph for what converts for this creator and return cited concept cards.",
            "parameters": {
                "type": "object",
                "properties": {"trend_label": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Semantic search over the graph memory: finds topics related to the "
                           "query, then the REAL videos on them (creator's with conversion ratio, "
                           "competitors', trending) with views/format/hook. Use for 'what have I "
                           "covered', 'who's winning on X', 'what works on this subject'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "scope": {
                        "type": "string",
                        "enum": ["all", "my_channel", "competitors", "trends"],
                        "description": "restrict to one node_set (default all)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quote_transcripts",
            "description": "Vector search over the actual video TRANSCRIPTS in memory — returns "
                           "verbatim passages of what was said on camera. Use for 'what did I say "
                           "about X', content-level questions, or pulling a quote. search_memory "
                           "knows titles and numbers; this knows the words.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "channel_watch",
            "description": "How the creator's latest uploads are ACTUALLY doing right now (fresh "
                           "public view counts vs their median), plus posting cadence and whether "
                           "they're overdue. Use whenever performance or timing comes up.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_outliers",
            "description": "The live trend waves and their overperforming evidence videos in the "
                           "niche right now. Use for 'what's hot', before recommending a direction.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_idea",
            "description": "The creator pitches a video idea — audit it against the memory: "
                           "evidence for/against, collisions, recommended treatment. Cited.",
            "parameters": {
                "type": "object",
                "properties": {"idea": {"type": "string"}},
                "required": ["idea"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_idea",
            "description": "Put an idea on the creator's board with a target publish date. Omit "
                           "target_date to schedule from their real cadence automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "target_date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_trend",
            "description": "Decay a dead trend wave out of the memory (removes its evidence "
                           "subgraph). Only on explicit request or clear staleness.",
            "parameters": {
                "type": "object",
                "properties": {"trend_label": {"type": "string"}},
                "required": ["trend_label"],
            },
        },
    },
]


async def _run_tool(name: str, args: dict) -> str:
    try:
        return await _run_tool_inner(name, args)
    except Exception as e:  # let the agent see and correct instead of a 500
        return f"tool error: {e}"


def _auto_target(cad: dict) -> str:
    from datetime import date, timedelta

    last = cad.get("last_published")
    gap = cad.get("median_gap_days")
    if last and gap:
        nxt = date.fromisoformat(last) + timedelta(days=gap)
        if nxt > date.today():
            return nxt.isoformat()
    return (date.today() + timedelta(days=2)).isoformat()


async def _run_tool_inner(name: str, args: dict) -> str:
    if name == "recall_suggestions":
        result = await suggest(args.get("trend_label") or None)
        slim = {
            "trend": result.get("trend"),
            "cards": [
                {k: c.get(k) for k in ("title", "angle", "hook", "format", "why", "citations")}
                for c in result.get("cards", [])
            ],
        }
        return json.dumps(slim, ensure_ascii=False)

    if name == "search_memory":
        # graph-native: vector hop to topics, then REAL videos with numbers.
        # (Verbatim transcript content is quote_transcripts' job.)
        scope = args.get("scope") or "all"
        g = await Graph.load()
        dists = await topic_distances(args["query"])
        median = g.my_median_views() or 1.0
        matches = []
        for tid, dist in sorted(dists.items(), key=lambda kv: kv[1]):
            if dist > 0.6 or tid not in g.props or len(matches) >= 6:
                continue
            videos = []
            for ns in ("my_channel", "competitors", "trends"):
                if scope != "all" and ns != scope:
                    continue
                for v in g.videos_covering(tid, ns)[:4]:
                    card = g.video_card(v)
                    item = {
                        "title": card["title"], "channel": card["channel"],
                        "views": card["views"], "published": card["published"],
                        "format": card["format"], "hook_style": card["hook_style"],
                        "source": ns,
                    }
                    if ns == "my_channel":
                        item["ratio_vs_median"] = round(card["views"] / median, 2)
                    videos.append(item)
            if videos:
                matches.append({
                    "topic": g.props[tid].get("label"),
                    "distance": round(dist, 3),
                    "videos": videos,
                })
        return json.dumps({"query": args["query"], "matches": matches}, ensure_ascii=False)

    if name == "quote_transcripts":
        from .cognee_context import with_user_cognee

        async with with_user_cognee():
            chunks = await cognee.search(
                query_text=args["query"], query_type=SearchType.CHUNKS, top_k=6
            )
        passages = []
        for c in chunks:
            text = str(c.get("text", ""))
            # Lane B docs start with a "VIDEO: <title>" header, so chunk 0 is
            # self-attributing; deeper chunks come back untitled — quote anyway.
            title = text.split("\n", 1)[0][7:] if text.startswith("VIDEO: ") else None
            passages.append({
                "video": title,
                "source_set": (c.get("belongs_to_set") or [None])[0],
                "text": text[:700],
            })
        return json.dumps({"query": args["query"], "passages": passages}, ensure_ascii=False)

    if name == "channel_watch":
        t = await get_track()
        cad = await cadence_route()
        return json.dumps({
            "median_views": t.get("median_views"),
            "uploads": [
                {k: u[k] for k in ("title", "views", "age_days", "ratio", "status")}
                for u in t.get("uploads", [])
            ],
            "memory_nodes_reweighted_from_these_numbers": t.get("improved_nodes"),
            "cadence": cad,
        }, ensure_ascii=False)

    if name == "list_outliers":
        data = await trends()
        return json.dumps([
            {
                "wave": t["label"],
                "peaked_at": t["peaked_at"],
                "evidence": [
                    {k: v[k] for k in ("title", "channel", "views", "published")}
                    for v in t["evidence_videos"]
                ],
            }
            for t in data
        ], ensure_ascii=False)

    if name == "review_idea":
        r = await review_idea(args["idea"])
        slim = {k: r.get(k) for k in
                ("verdict", "confidence", "fit", "evidence_for", "evidence_against",
                 "collisions", "recommended", "citations")}
        return json.dumps(slim, ensure_ascii=False)

    if name == "plan_idea":
        target = args.get("target_date") or _auto_target(await cadence_route())
        idea = lifecycle_save(args["title"], state="planted", provenance="chat")
        return json.dumps({"planned": idea["id"], "title": idea["title"], "target": target})

    if name == "forget_trend":
        res = await forget_trend(args["trend_label"])
        return json.dumps(res, ensure_ascii=False)

    return f"unknown tool {name}"


@app.post("/chat")
async def chat_route(body: ChatBody):
    return await agent_chat(body.message, body.history)

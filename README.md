# Sprout

**Memory that gets sharper, not just bigger.**

Sprout is a quiet creator companion with a persistent memory of *you*. Sign in with YouTube once — it reads your real analytics, tells you your own genre, and builds one weighted graph of what you make and what converts for you. From then on it does the research you'd otherwise doomscroll for: trends in your true niche, your real competitors, what your audience actually responds to — and brings it back as calm, cited, falsifiable suggestions you react to with one tap.

Every reaction makes the memory sharper. Every idea you mention is quietly caught, grown on a vision board (**seed → planted → sprouted**), and celebrated when you post. The promise: **create more, consume less** — and never open YouTube Studio just to *check*.

Built for the **WeMakeDevs × Cognee hackathon** ("The Hangover"). Python package name: `memory_shield`.

---

## Table of contents

- [Try it](#try-it)
- [How it actually works (start here)](#how-it-actually-works-start-here)
- [User journeys](#user-journeys)
- [The three surfaces](#the-three-surfaces)
- [Why Sprout exists](#why-sprout-exists)
- [Memory system](#memory-system)
- [Data pipeline](#data-pipeline)
- [Analytics ingestion](#analytics-ingestion)
- [Transcripts](#transcripts)
- [Architecture](#architecture)
- [Multi-user & storage](#multi-user--storage)
- [Graph schema](#graph-schema)
- [Cognee integration](#cognee-integration)
- [Chat agent & tools](#chat-agent--tools)
- [API reference](#api-reference)
- [Frontend routes](#frontend-routes)
- [Tech stack](#tech-stack)
- [Project layout](#project-layout)
- [Local development](#local-development)
- [Environment variables](#environment-variables)
- [Deployment](#deployment)
- [Demo script](#demo-script)
- [Known limitations](#known-limitations)
- [Documentation index](#documentation-index)

---

## Try it

| Surface | URL |
|---|---|
| **Live frontend** | [sprout-frontend-1041216984106.us-central1.run.app](https://sprout-frontend-1041216984106.us-central1.run.app) |
| **Live API** | [sprout-backend-1041216984106.us-central1.run.app/health](https://sprout-backend-1041216984106.us-central1.run.app/health) |
| **Demo studio** (no sign-in) | [/studio](https://sprout-frontend-1041216984106.us-central1.run.app/studio) |
| **Real-user signup** | [/signup](https://sprout-frontend-1041216984106.us-central1.run.app/signup) |

**Target custom domains:** `sprout.asad.codes` (frontend) · `api.sprout.asad.codes` (backend) — DNS cutover pending.

**Legacy VM fallback:** `35.193.172.43` (do not delete until Cloud Run custom-domain smoke test passes).

---

## How it actually works (start here)

If the codebase feels overwhelming, the **user-facing product** is simpler than the architecture:

> **Connect once → memory builds itself from YouTube data → the dashboard shows cited ideas → you react (plant, thumbs, chat) → memory sharpens.**

### What builds memory (automatic — not a chat questionnaire)

Memory is **not** created by interviewing the user in chat. It comes from a **batch pipeline**:

1. **Fetch** channel videos, competitors, trends (YouTube Data API)
2. **Transcripts** + LLM extraction (topics, hooks, formats, beats)
3. **Analytics** (real OAuth Analytics API, or synthetic fixture for demo)
4. **Pattern scan** (pandas — CTR, retention, pacing correlations with `n`)
5. **Cognee ingest** (typed graph + transcript cognify)
6. **Fingerprint** (genre distribution weighted by conversion)

The pitch beat *"Your last 40 videos are really three things — right?"* is **designed** as an onboarding reveal. Today it surfaces as **UI copy** on the signup reveal screen (from `fingerprint.py`), not as an interactive chat confirm loop.

### What the user actually touches

| Surface | Role | Requires chat? |
|---|---|---|
| **Today tab** (`/studio`) | Cited concept cards, pitch review, thumbs feedback | No |
| **Board tab** | Vision board — planted ideas, production kit | No |
| **Library tab** | Channel + competitor shelf | No |
| **Chat dock** | Agent over the memory — optional depth | Yes (you initiate) |
| **Telegram** | Ambient nudges + quick replies | Optional |

Chat **does** respond to casual messages like "hi" — it uses a frontier model with Sprout's system prompt. It won't call tools for greetings; it will for factual asks like *"how are my uploads doing?"*

### The core loop

```
analytics + corpus  →  remember (ingest)  →  recall (killer query / cards)
        ↑                                              ↓
   refresh cron                                  user reacts
        ↑                                              ↓
   track / nudges  ←  improve / forget  ←  thumbs / confirm / sprout
```

**Batch eagerly, retrieve lazily:** patterns and analytics refresh on a schedule; chat and `/suggest` read caches, not live YouTube on every request.

---

## User journeys

### Demo path (judges, local dev, no Firebase)

1. Open **`/studio`** — no account needed.
2. Backend defaults to `uid=demo` when no Firebase Bearer token is present.
3. On first boot (Postgres prod), auto-ingests **@LanaBlakely** corpus + synthetic analytics.
4. **Today** loads concept cards for `"slow living"`; **Board** starts empty until you tap ✨ Create.

```bash
# Local: ensure corpus + graph exist
cd backend
python -m memory_shield.corpus
python -m memory_shield.ingest --fresh   # stop uvicorn first (Kuzu single-writer)
uvicorn memory_shield.api:app --reload --port 8000
cd ../frontend && npm run dev
# → http://localhost:3000/studio
```

### Real-user path

1. **`/signup`** — Firebase Google sign-in (identity only).
2. **YouTube OAuth** — `GET /auth/youtube/url` → callback stores encrypted refresh token.
3. **`POST /onboarding/start`** — UI wizard (not chat): fetch → extract → ingest → fingerprint.
4. **Cold-start** (<10 videos): must declare niche via `POST /onboarding/niche` before build.
5. **Reveal screen** — genre summary text → **Open my studio**.
6. Per-user Cognee dataset created; up to **10 real users** (`MAX_USERS`).

Sign-in setup: [.github/SIGNIN_SETUP.md](.github/SIGNIN_SETUP.md)

---

## The three surfaces

### Today (`/studio` → Today tab)

- **Concept cards** from `GET /suggest?trend=…` — killer graph join, citation thumbnails, trace for graph drawer.
- **✨ Create** → `POST /ideas` — saves title to board as `planted`.
- **Thumbs** (nailed it / not me) → `POST /feedback` → `improve()` on Topic/Hook/Format nodes.
- **Pitch box** → `POST /review` — audit your idea against memory.
- **Outlier strip** — trend waves; pick one to re-run suggest; forget stale trends.
- **Skeptic stack** — RAG contrast (`/contrast`), temporal holdout backtest (`/backtest`).
- **Your garden** (collapsible) — seeds, planted, sprouted + consistency headline.

### Board (`/studio` → Board tab)

REST-driven vision board (`GET/POST/PATCH/DELETE /ideas`):

| Action | API | Status |
|---|---|---|
| List ideas | `GET /ideas` | ✅ |
| Save from concept card | `POST /ideas` | ✅ (title + state) |
| Plant seed | `POST /ideas/{id}/plant` | ✅ |
| Production kit (shoot brief) | `GET /ideas/{id}/production-kit` | ✅ when `planted` |
| Delete | `DELETE /ideas/{id}` | ✅ |
| Status dropdown | `PATCH /ideas/{id}` | ✅ |
| Target date picker | `PATCH` with `target` | ⚠️ not persisted yet (see [Known limitations](#known-limitations)) |
| Card/trace detail view | needs `payload` on draft | ⚠️ not persisted yet |

Chat can also write ideas via **`save_idea`** tool (same Postgres `drafts` table).

### Chat (`ChatDock` → `POST /chat`)

- Uses **`agent.py`** (frontier model, default `gpt-4o`).
- **Context pack** injected every turn (no tool): genre, prefs, seeds/planted preview, digest, baselines.
- **Read tools** when facts needed; **write tools** only on explicit user command.
- **Silent seed capture** after each reply — regex on user+assistant text → `save_idea(state=seed)`.
- Telegram bot uses the same `agent.chat()`.

---

## Why Sprout exists

Most creator tools score your title against *everyone's* videos. Sprout validates it against *yours* — computed receipts like `2.1× CTR, n=5`, confirm/deny → memory reweights → next suggestion is measurably more *you*.

**ChatGPT is a brilliant stranger every session. Sprout is the same brain that's known you for months.**

### Three moats

1. **Private analytics** — retention, CTR, impressions (OAuth Analytics API)
2. **Niche graph with per-competitor baselines** — outlier score vs each channel's own median, not raw views
3. **Compounding weighted memory** — Cognee `remember` / `recall` / `improve` / `forget`

### vs vidIQ / TubeBuddy

They score against global top performers and invent "estimated CTR." Sprout validates against **your portfolio** with computed `n` and sample sizes. You can say "that pattern doesn't work for me" and it **remembers**.

---

## Memory system

Memory is **four layers**, not one file:

| Layer | Contents | Store | How it updates |
|---|---|---|---|
| **Graph** | Videos, Topics, Hooks, Patterns, Trends, weights | Cognee per-user dataset | Ingest, refresh, `improve()`, `forget()` |
| **Analytics** | CTR, retention, growth score per video | Postgres `analytics_*` | Onboarding + hourly refresh |
| **Preferences** | tone, goals, interruption budget, exclusions | Postgres `preferences` | `set_preference` tool / API |
| **Board** | seeds, planted, sprouted drafts | Postgres `drafts` | REST `/ideas`, `save_idea` tool, lifecycle |

### Preferences (read vs write)

**Read:** automatic — every chat turn injects `get_preferences()` in the context pack. No tool call.

**Write:** via agent tools when user explicitly asks:

- `set_preference` — `interruption_budget`, `tone`, `goals`, `competitor_alerts`
- `remove_competitor` — adds to `competitor_exclusions` (Postgres + Cognee `PreferenceNode`)

**Dual write:** Postgres is source of truth; writes also mirror a `PreferenceNode` into Cognee for graph queries.

`declared_niche` (cold-start) is set via **`POST /onboarding/niche`**, not the chat agent.

### Feedback / learning paths

| Trigger | Mechanism |
|---|---|
| Thumbs on concept card | `POST /feedback` → `improve(trace, ±25)` |
| Pattern confirm in chat | `confirm_pattern` tool → `improve()` on evidence trail |
| Posted video / sprout | `mark_sprouted()` → bumps Topic/Format weights |
| Upload performance | `GET /track` → auto `improve()` from public view deltas |
| Stale trends | `POST /decay` or cron → `forget_trend()` |
| Unplanted seeds | refresh cron → `compost_stale_seeds()` (21 days) |

Chat history (last 8 turns) is **not** stored in the graph — only distilled idea cards.

---

## Data pipeline

### Corpus build (`python -m memory_shield.corpus`)

For each video (creator, competitors, trends):

```
YouTube Data API  →  transcript (youtube-transcript-api, cached)
                  →  extract_video() — 1–4 topics, hook, format (gpt-4o-mini)
                  →  segment_beats() — intro/demo/cta timestamps (gpt-4o-mini)
```

**Holdout partition:** videos after `HOLDOUT_CUTOFF` (2026-04-01 for @LanaBlakely) go to `corpus["holdout"]` — never ingested into the live graph (backtest reveal reads them from cache).

**Demo corpus limits** (`config.py`):

| Setting | Value |
|---|---|
| Creator videos | 60 most recent (pre-partition) |
| Competitors | `@struthless`, `@MattDAvella`, `@lavendaire`, `@muchelleb`, `@TheFinancialDiet`, `@PickUpLimes` — 8 videos each |
| Trend keywords | slow living, digital minimalism, morning routine habits, self care routine, intentional living — 4 videos each |
| Niche label | slow-living and self-improvement vlogging |

### Two-lane Cognee ingest (`python -m memory_shield.ingest`)

**Lane A** — `add_data_points()` (deterministic, no LLM):

- `Creator`, `Video`, `Topic`, `Hook`, `Format`, `Trend`, `PatternNode`
- Edges: `Video-covers→Topic`, `Video-uses→Hook`, `Video-has_format→Format`, `Video-exhibits→PatternNode`, `Trend-evidenced_by→Video`
- Each video: **1–4 Topic nodes**, exactly **1 Hook**, **1 Format**

**Lane B** — `add()` + `cognify(temporal_cognify=True)`:

- Full transcript docs (6k chars) per video → semantic search (`quote_transcripts`, RAG contrast)
- Skipped if no transcripts available (IP block backfill pending)

### Pattern analyzer (`analyzer.py`)

- **All math in pandas** over analytics table — never LLM-estimated numbers
- Stratified by `is_short` (Shorts vs long-form never pooled)
- Confidence tiers: `n=2` early signal · `n≥3` validated
- **Pacing patterns:** beats × retention — e.g. intro >40s bleeds retention
- Results → `PatternNode`s with `exhibits` edges

### Killer query (`recall.py` → `GET /suggest`)

Hand-orchestrated multi-step retrieval — **not** a single `search()`:

1. Bridge trend label → your converting Topics (vector + one graph hop)
2. Filter to your fingerprint
3. Pull competitor/trend evidence ranked by **outlier score** (views ÷ channel median)
4. Apply `feedback_weight` re-ranking
5. LLM synthesizes cited concept cards with trace (topics, hooks, formats for `improve()`)

**Gap finder** (`GET /gaps`): graph anti-join — trending topics near your fingerprint with no path to topics you already cover.

---

## Analytics ingestion

**Not live on every request.** Scheduled batch + cached reads.

| Data | Source | When fetched |
|---|---|---|
| **Private analytics** (retention, CTR, traffic) | YouTube Analytics API (OAuth) | Onboarding + each refresh tick |
| **Public view counts** | YouTube Data API | Each refresh tick + `/track` (6h cache) |
| **Demo analytics** | `analytics_fixture.py` synthetic world | Demo user / no OAuth |

### Refresh loop

On server startup, in-process asyncio loop every **`REFRESH_INTERVAL_SECONDS`** (default **3600** = 1 hour):

For each user with `onboarding_status == "ready"`:

1. Re-pull analytics (`build_analytics_real` or fixture)
2. Recompute patterns → write PatternNodes
3. Rebuild fingerprint
4. `poll_live_stats()` — snapshot recent upload views
5. `get_track(force=True)` — auto `improve()` from view deltas
6. `compost_stale_seeds()`
7. Optional Telegram nudges (respects `interruption_budget`)

**External cron** (Cloud Scheduler):

```http
POST /internal/cron/refresh       # full refresh
POST /internal/cron/live-stats    # view-count polling only
Header: x-cron-secret: <CRON_SECRET>
```

Corpus/trends are **not** rebuilt every tick — only on onboarding or `rebuild_corpus=True`.

---

## Transcripts

Fetched once at corpus build via `youtube-transcript-api` (public captions, throttled, disk-cached). **Not re-fetched on refresh.**

| Use | How |
|---|---|
| Topic/hook/format extraction | First ~500 chars of transcript → `extract.py` |
| Beat segmentation | Up to 8k chars → pacing patterns (intro >40s bleeds) |
| Lane B cognify | Full text → `CHUNKS` search, RAG contrast, `quote_transcripts` tool |
| Graph Video node | Stores **beats**, not raw transcript text |

Without transcripts: Lane B skipped, pacing patterns degraded, extraction falls back to title-only.

Re-run `python -m memory_shield.corpus` after YouTube IP block lifts to backfill.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  SOURCES                                                        │
│  YouTube Data API · Analytics API (OAuth) · Reddit/HN · Demo    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  .cache/  — transcripts, extractions, packaging, concept art    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Analytics table (pandas) — ALL numbers, confidence tiers, n    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Cognee graph + pgvector — node_sets, PatternNodes, weights   │
│  my_channel · competitors · trends · drafts                     │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agent (gpt-4o) + tools · context pack every turn               │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Next.js garden (/studio) · Telegram bot                        │
└────────────────────────────┬────────────────────────────────────┘
                             ▲
┌─────────────────────────────────────────────────────────────────┐
│  Refresh cron — analytics, patterns, live stats, compost, nudges│
└─────────────────────────────────────────────────────────────────┘
```

### Division of labor

| Layer | Role |
|---|---|
| **LLM** (`gpt-4o-mini`, batch) | Labels: topics, hooks, formats, beats. **Never arithmetic.** |
| **Vision** | Static thumbnail packaging (one cached call/video) |
| **Python / pandas** | CTR, retention, correlations, effect sizes, rankings |
| **Cognee** | Store, join, reweight, forget — does not invent patterns |
| **Frontier LLM** (`gpt-4o`, chat) | User-facing phrasing + tool orchestration |

### Cold-start tiers

| Tier | Videos | Behavior |
|---|---|---|
| `empty` | 0 | Declared niche required; trend-based suggestions only |
| `warming` | 1–9 | No validated patterns; honest "too few for n=3" framing |
| `established` | 10+ | Full fingerprint + pattern pipeline |

Threshold: `CATALOG_ESTABLISHED_MIN = 10` in `config.py`.

---

## Multi-user & storage

### Auth (two-step for real users)

1. **Firebase** — Google sign-in, Bearer ID token on every API call
2. **Google OAuth** — separate flow for YouTube Analytics refresh token (encrypted in `oauth_credentials`)

Demo: no token → auto `uid=demo`.

### Three logical databases (production Cloud SQL)

| Database | Contents |
|---|---|
| **`sprout_app`** | `users`, `oauth_credentials`, `preferences`, `drafts`, `analytics_*`, `fingerprints`, `video_stats_snapshots` |
| **`cognee_meta`** | Cognee relational tables (`ENABLE_BACKEND_ACCESS_CONTROL=true`) |
| **Per-user dataset DBs** | Graph + pgvector (max 10 creators) |

Every Cognee call in multi-user paths runs inside **`user_cognee_context(dataset_id, user_id)`**.

### Local dev fallback

| Piece | Local |
|---|---|
| App state | SQLite `backend/.cache/sprout_app.db` |
| Graph | Kuzu + LanceDB under `backend/.cognee/` |
| Cognee access control | `ENABLE_BACKEND_ACCESS_CONTROL=false` |

**Rule:** stop uvicorn before `python -m memory_shield.ingest` locally (Kuzu single-writer). Postgres prod has no file lock.

---

## Graph schema

Cognee `DataPoint` subclasses in `graph_models.py`:

| Node | Key fields / edges |
|---|---|
| `Creator` | name, niche, handle |
| `Video` | metrics, `is_short`, `beats[]` → `covers` Topic, `uses` Hook, `has_format` Format, `exhibits` PatternNode |
| `Topic` | label (embedded) — **1–4 per video** |
| `Hook` | text, style |
| `Format` | name (talking-head, personal-essay, vlog, …) |
| `Trend` | label, peaked_at → `evidenced_by` Videos |
| `PatternNode` | kind, support_n, effect_size, metric, confidence, evidence_video_ids |
| `Preference` | key, value (mirrored from Postgres writes) |

**node_sets:** `my_channel` · `competitors` · `trends` · `drafts`

**Holdout:** post-2026-04-01 videos excluded from live graph for backtest.

---

## Cognee integration

| Op | Sprout usage |
|---|---|
| **`remember`** | Lane A skeleton + Lane B cognify; scoped `node_set`s; per-user datasets |
| **`recall`** | Killer query orchestration; semantic topic bridge; `feedback_weight` re-rank |
| **`improve`** | Thumbs, pattern confirm, sprout, track — native `set_node_feedback_weights` |
| **`forget`** | Trend dataset decay (`trends_YYYY_WWW`), seed compost, competitor exclusion |

### Why not plain RAG?

1. **The join** — multi-hop: your converting Topics → trend/competitor Videos → filtered Creators (0.3×–10× sub band)
2. **The anti-join** — gap-finder: trending near fingerprint, no path to covered topics
3. **Weighted learning** — numeric reweight, not appended notes

Side-by-side proof: `GET /contrast` — plain `search(CHUNKS)` vs killer join on the same question.

---

## Chat agent & tools

**Entry:** `POST /chat` → `agent.py` · Model: `CHAT_MODEL` (default `gpt-4o`)

### Context pack (automatic, every turn)

`cold_start`, `genre`, `baselines`, `seeds_preview`, `planted`, `recent_sprouted`, `digest`, `preferences`

### Agent tools

| Tool | Read/Write | Purpose |
|---|---|---|
| `get_my_performance` | Read | PatternNodes + analytics slices |
| `recall_suggestions` | Read | Killer query concept cards |
| `get_drafts` / `get_seeds` | Read | Vision board / seed tray |
| `save_idea` | Write | Save or plant idea |
| `check_competitors` | Read | Triangulated competitor set |
| `scan_trends` | Read | Trend waves + evidence |
| `confirm_pattern` | Write | Hypothesis confirm → `improve()` |
| `forget_trend` | Write | Decay trend (confirm first) |
| `search_discourse` | Read | Reddit + HN × fingerprint |
| `remove_competitor` | Write | Durable exclusion |
| `set_preference` | Write | tone, goals, interruption budget |

**Rules:** no number without a tool result · write tools on explicit command only · destructive ops confirm first.

---

## API reference

All routes on backend `:8000`. Demo works without auth; real users send `Authorization: Bearer <Firebase ID token>`.

### Studio & memory

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness |
| `GET` | `/suggest?trend=` | Cited concept cards (killer query) |
| `GET` | `/garden` | Home surface: consistency, seeds, planted, plants |
| `GET` | `/trends` | Trend waves + evidence videos |
| `GET` | `/library` | Creator + competitors + holdout metadata |
| `GET` | `/fingerprint` | Genre + competitor triangulation |
| `GET` | `/patterns` | Computed PatternNodes list |
| `GET` | `/analytics` | Full analytics payload |
| `GET` | `/graph` | Graph visualization payload |
| `GET` | `/gaps?trend=` | Gap-finder anti-join |
| `GET` | `/backtest` | Temporal holdout reveal |
| `GET` | `/contrast?trend=` | RAG vs killer join side-by-side |
| `GET` | `/cadence` | Posting rhythm from publish dates |
| `GET` | `/track` | Near-live upload performance + auto improve |
| `GET` | `/pulse` | Discourse radar (HN + Reddit) |
| `POST` | `/review` | Audit a pitched idea |
| `POST` | `/feedback` | `{ trace, performance_pct }` → improve |
| `POST` | `/decay` | Forget a trend |
| `POST` | `/chat` | Agent chat `{ message, history }` |
| `POST` | `/thumbnail-review` | Vision thumbnail audit |

### Vision board (`/ideas`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/ideas?state=` | List drafts (optional filter: seed/planted/sprouted) |
| `POST` | `/ideas` | Create draft `{ title, source, payload, target }` |
| `PATCH` | `/ideas/{id}` | Update `{ status, target }` |
| `DELETE` | `/ideas/{id}` | Delete draft |
| `POST` | `/ideas/{id}/plant` | seed → planted (+ concept art + production kit) |
| `GET` | `/ideas/{id}/production-kit` | Script skeleton + thumbnail brief |
| `POST` | `/ideas/{id}/sprout` | Mark posted → reweight graph |

### Auth & onboarding

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/youtube/url` | Start YouTube OAuth |
| `GET` | `/auth/youtube/callback` | OAuth callback |
| `POST` | `/onboarding/start` | Begin per-user ingest |
| `GET` | `/onboarding/status` | Poll stage + genre preview |
| `POST` | `/onboarding/niche` | Cold-start declared niche |
| `POST` | `/connect` | Demo-only rebuild (`uid=demo`) |
| `GET` | `/connect/status` | Demo onboarding status |

### Telegram

| Method | Path | Description |
|---|---|---|
| `GET` | `/telegram/link` | Per-user deep link token |
| `GET` | `/telegram/status` | Linked chat id (masked) |
| `GET` | `/telegram/poll` | Poll once (local dev fallback) |
| `GET` | `/telegram/nudge` | Send test nudge |
| `POST` | `/telegram/send` | Push nudge to linked user |

### Internal cron

| Method | Path | Description |
|---|---|---|
| `POST` | `/internal/cron/refresh` | Full per-user refresh |
| `POST` | `/internal/cron/live-stats` | View-count snapshots only |

---

## Frontend routes

| Route | Purpose |
|---|---|
| `/` | Landing — product story, core loop animation |
| `/studio` | Main dashboard (Today · Board · Library) + chat dock + graph drawer |
| `/signup` | Real-user onboarding wizard |
| `/connect` | Redirects to `/signup` |

Key components: `ConceptCard`, `IdeasBoard`, `ProductionKit`, `ChatDock`, `GraphPanel`, `BacktestReveal`, `RagContrast`, `SproutDashboard`, `PitchBox`.

Static concept art served at `/concept-art/*` when `CONCEPT_ART_ENABLED=true`.

---

## Tech stack

| Piece | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Cognee 1.2.2 |
| Frontend | Next.js 16, React 19, Tailwind v4, Motion |
| Graph + vectors | Postgres + pgvector (prod) · Kuzu + LanceDB (local) |
| App state | SQLModel · Postgres (prod) · SQLite (local) |
| Auth | Firebase Admin + Google OAuth (YouTube Analytics) |
| LLM batch | OpenAI `gpt-4o-mini` (extract, beats, card synthesis) |
| LLM chat | OpenAI `gpt-4o` (configurable via `CHAT_MODEL`) |
| Deploy | GCP Cloud Run + Cloud SQL · GitHub Actions |
| Secrets | GCP Secret Manager (prod) |
| Proactive | Telegram bot (long-poll in uvicorn lifespan) |

---

## Project layout

```
cognee-hackathon/
├── backend/memory_shield/
│   ├── api.py              # FastAPI routes + lifespan (refresh, Telegram poll)
│   ├── agent.py            # Chat agent + tool dispatch
│   ├── recall.py           # Killer query, gap_finder, suggest
│   ├── ingest.py           # Two-lane Cognee ingest
│   ├── corpus.py           # Fetch + enrich + holdout partition
│   ├── transcripts.py      # youtube-transcript-api + cache
│   ├── extract.py          # topics + hook + format (1 LLM call/video)
│   ├── beats.py            # transcript → structural beats
│   ├── analyzer.py         # Pattern computation (pandas)
│   ├── analytics_fixture.py / analytics_youtube.py
│   ├── fingerprint.py      # Genre distribution
│   ├── onboarding.py       # Per-user pipeline
│   ├── refresh.py          # Background refresh loop
│   ├── live_stats.py       # Near-live view polling
│   ├── lifecycle.py        # seeds → planted → sprouted
│   ├── preferences.py      # Postgres + Cognee preference mirror
│   ├── production_kit.py   # Shoot brief generator
│   ├── ops.py              # improve() + forget_trend()
│   ├── track.py            # Auto improve from upload views
│   ├── nudges.py           # Proactive Telegram messages
│   ├── telegram_bot.py     # Bot + per-user linking
│   ├── contrast.py         # RAG vs graph demo
│   ├── graph_models.py     # Cognee DataPoint schema
│   ├── cognee_context.py   # Per-user isolation wrapper
│   ├── db/                 # SQLModel models, repos, sessions
│   ├── auth/               # Firebase + YouTube OAuth
│   └── scripts/
│       ├── phase0_smoke.py # Postgres + Cognee gate test
│       └── test_telegram_e2e.py
├── frontend/
│   ├── app/studio/         # Dashboard
│   ├── app/signup/         # Onboarding wizard
│   ├── components/         # UI building blocks
│   └── lib/api.ts          # Typed API client + Firebase auth headers
├── scripts/
│   ├── gcp-provision-sql.sh
│   ├── bootstrap-gcp-secrets.sh
│   ├── setup-github-wif.sh
│   └── gcp-deploy.sh
├── .github/workflows/      # ci.yml + deploy.yml
├── CLAUDE.md               # Authoritative build spec (agents)
├── DESIGN.md               # Human-readable product explainer
├── BUILD.md                # What's real vs stubbed snapshot
└── DEMO_SCRIPT.md          # 90-second judge walkthrough
```

---

## Local development

### Prerequisites

- Python 3.11+
- Node.js 20+
- OpenAI API key (`LLM_API_KEY`)
- YouTube Data API v3 key (`YOUTUBE_API_KEY`)

### Setup

```bash
git clone https://github.com/YOUR_ORG/cognee-hackathon.git
cd cognee-hackathon

cp .env.example .env
# Required: LLM_API_KEY, YOUTUBE_API_KEY

cp frontend/.env.local.example frontend/.env.local
# Firebase optional — /studio demo works without it

python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Build demo memory (first time)

```bash
cd backend
python -m memory_shield.corpus          # → .cache/corpus.json
python -m memory_shield.ingest --fresh # ⚠ stop uvicorn first (Kuzu single-writer)
```

### Run

```bash
# Terminal 1
cd backend && uvicorn memory_shield.api:app --reload --port 8000

# Terminal 2
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000/studio](http://localhost:3000/studio).

### Optional: Cloud SQL locally

```bash
export SPROUT_DATABASE_URL=postgresql+asyncpg://postgres:PASS@HOST:5432/sprout_app
export DB_HOST=HOST DB_PASSWORD=PASS DB_NAME=cognee_meta
python -m memory_shield.scripts.phase0_smoke
```

### Operational rules

- **Import `memory_shield.config` before `cognee`** — env roots must be pinned first (`cognee_env.py`)
- **Local Kuzu:** stop uvicorn before ingest; production Postgres has no file lock
- **Every Cognee call** in multi-user paths must use `user_cognee_context()`
- **Transcript IP blocks:** negative misses cached; re-run corpus when block lifts — never cache block failures as permanent
- **Cloud Run:** `min-instances=1` keeps Telegram poll + refresh loop alive; onboarding timeout up to 3600s
- **After `improve()`:** suggest cache invalidated (feedback weights changed)

### Sanity checklist

1. `GET /health` → `{"ok":true}`
2. `/studio` → concept cards load on Today
3. ✨ Create on a card → appears on Board tab
4. Chat: "hi" → friendly reply; "what should I make about slow living?" → may show tool calls
5. Thumbs on card → next suggest may reorder

---

## Environment variables

### Root `.env` (see [`.env.example`](.env.example))

| Key | Required | Purpose |
|---|---|---|
| `LLM_API_KEY` | **Yes** | OpenAI — Cognee + extraction + chat |
| `YOUTUBE_API_KEY` | **Yes** | Data API — corpus, live stats, competitors |
| `CHAT_MODEL` | No | Chat agent model (default `gpt-4o`) |
| `CREATOR_HANDLE` | No | Demo channel (default `@LanaBlakely`) |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | Real users | YouTube Analytics OAuth |
| `GOOGLE_OAUTH_REDIRECT_URI` | Real users | Default `https://api.sprout.asad.codes/auth/youtube/callback` |
| `SPROUT_DATABASE_URL` | Prod | Postgres app state (unset → SQLite local) |
| `DB_HOST/PORT/USERNAME/PASSWORD/NAME` | Prod | Cognee meta DB (`cognee_meta`) |
| `FIREBASE_SERVICE_ACCOUNT_FILE` or JSON env | Real users | Firebase Admin token verification |
| `FRONTEND_URL` | Prod | OAuth redirects |
| `CORS_ORIGINS` | Prod | Comma-separated allowed origins |
| `CRON_SECRET` | Prod | Protects `/internal/cron/*` |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot |
| `TELEGRAM_LINK_SECRET` | Optional | HMAC for `/telegram/link` tokens |
| `TELEGRAM_CHAT_ID` | Optional | Legacy single-chat fallback |
| `REFRESH_INTERVAL_SECONDS` | No | Background refresh interval (default 3600; 0 disables) |
| `CONCEPT_ART_ENABLED` | No | `gpt-image-1` concept art on plant (default false) |
| `MAX_USERS` | No | Real user cap (default 10) |

**Production Cognee env** (auto-set when `SPROUT_DATABASE_URL` is Postgres):

`ENABLE_BACKEND_ACCESS_CONTROL=true` · `GRAPH_DATABASE_PROVIDER=postgres` · `VECTOR_DB_PROVIDER=pgvector` · etc.

### Frontend `frontend/.env.local`

| Key | Purpose |
|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase Auth |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase Auth |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase Auth |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase Auth |
| `NEXT_PUBLIC_API_BASE` | Backend URL (default `http://localhost:8000`) |

---

## Deployment

**GCP project:** `sprout-cognee-hackathon` · **Region:** `us-central1`

| Service | Name |
|---|---|
| Backend | `sprout-backend` (min-instances=1, timeout=3600) |
| Frontend | `sprout-frontend` |
| Database | Cloud SQL `sprout-db` (Postgres 15, pgvector) |

### One-time setup

```bash
./scripts/gcp-provision-sql.sh       # Cloud SQL + databases
./scripts/bootstrap-gcp-secrets.sh   # .env → Secret Manager
./scripts/setup-github-wif.sh        # GitHub Actions WIF auth
```

### Deploy

- **Auto:** push to `main` → `.github/workflows/deploy.yml`
- **Manual:** `./scripts/gcp-deploy.sh`

Full guide: [.github/DEPLOY.md](.github/DEPLOY.md) · Sign-in: [.github/SIGNIN_SETUP.md](.github/SIGNIN_SETUP.md)

### Phase 0 gate (Postgres)

```bash
export SPROUT_DATABASE_URL=...
export DB_HOST=... DB_PASSWORD=... DB_NAME=cognee_meta
python -m memory_shield.scripts.phase0_smoke
```

---

## Demo script

90-second judge walkthrough — full script in [DEMO_SCRIPT.md](DEMO_SCRIPT.md):

1. **Hook** — "Memory that gets sharper, not just bigger."
2. **Proof strip** — citation thumbnails on a concept card
3. **Graph drawer** — Trend → Topic → Video → Format path
4. **Skeptic stack** — RAG contrast → sealed backtest → reveal held-out winners
5. **Workflow** — ✨ Create → Board → production kit
6. **Close** — "Post it — memory sharpens from your uploads automatically."

**Demo spine:** onboarding reveal → Monday cards → retro payoff → one-tap skew.

**Centerpiece:** temporal holdout — graph blind after **2026-04-01**; reveal names Lana's actual holdout hits (*"Losing my hearing: 2 years later"*, *"When people ask why I'm still single…"*).

---

## Known limitations

Honest gaps as of Jul 2026 hackathon build:

| Area | Status |
|---|---|
| Vision board `payload` (card + trace) | Frontend sends it; backend `Draft` model doesn't persist — board detail view thin |
| Target publish date on drafts | `PATCH target` silently ignored — no DB column yet |
| Genre reveal "— right?" confirm | UI display only; no interactive reweight from user correction in chat |
| Transcript backfill | YouTube IP blocks can leave Lane B / pacing patterns partial |
| Corpus refresh on cron | Trends/competitors not re-fetched hourly — onboarding/CLI only |
| Discourse radar | Reddit 403 on some networks; HN fallback |
| Real OAuth | Requires Google consent screen test users (≤100) |
| `api.py` `_AGENT_TOOLS` | Extended tool set defined but **`/chat` uses `agent.py`** — not wired to extended set |

See [BUILD.md](BUILD.md) for a build-state snapshot.

---

## Documentation index

| Doc | Audience | Contents |
|---|---|---|
| [DESIGN.md](DESIGN.md) | Humans | Full product story, one-tap mechanics, architecture narrative |
| [CLAUDE.md](CLAUDE.md) | Agents / builders | Terse spec, env facts, Cognee API, cut-lines, deploy commands |
| [BUILD.md](BUILD.md) | Builders | What's real vs stubbed (Jul 5 snapshot) |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Presenters | Judge demo beats |
| [.github/DEPLOY.md](.github/DEPLOY.md) | Ops | GitHub Actions + Secret Manager |
| [.github/SIGNIN_SETUP.md](.github/SIGNIN_SETUP.md) | Ops | Firebase + OAuth console steps |

---

## License

Hackathon submission — see repository for license terms.

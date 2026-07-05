# Sprout

**Memory that gets sharper, not just bigger.**

Sprout is a quiet creator companion with a persistent memory of *you*. Sign in with YouTube once — it reads your real analytics, tells you your own genre, and builds one weighted graph of what you make and what converts for you. From then on it does the research you'd otherwise doomscroll for: trends in your true niche, your real competitors, what your audience actually responds to — and brings it back as calm, cited, falsifiable suggestions you react to with one tap.

Every reaction makes the memory sharper. Every idea you mention is quietly caught, grown on a vision board (**seed → planted → sprouted**), and celebrated when you post. The promise: **create more, consume less** — and never open YouTube Studio just to *check*.

Built for the [WeMakeDevs × Cognee hackathon](https://wemakedevs.com/) ("The Hangover"). Python package name: `memory_shield`.

---

## Try it

| Surface | URL |
|---|---|
| **Live app** | [sprout-frontend-1041216984106.us-central1.run.app](https://sprout-frontend-1041216984106.us-central1.run.app) |
| **API** | [sprout-backend-1041216984106.us-central1.run.app/health](https://sprout-backend-1041216984106.us-central1.run.app/health) |
| **Demo studio** (no sign-in) | [/studio](https://sprout-frontend-1041216984106.us-central1.run.app/studio) |

**Two paths:**

- **Demo** — open `/studio` with no account. Runs the real system on a fixed synthetic world ([@LanaBlakely](https://youtube.com/@LanaBlakely) corpus + fabricated-but-internally-consistent analytics). Every number the agent cites is truthful relative to that world.
- **Real** — Firebase sign-in → YouTube OAuth → per-user onboarding with your private Analytics API data (retention, CTR, traffic sources, subs gained).

Custom domains (`sprout.asad.codes`, `api.sprout.asad.codes`) are wired in GCP; DNS cutover pending.

---

## Why Sprout exists

Most creator tools score your title against *everyone's* videos. Sprout validates it against *yours* — computed receipts like `2.1× CTR, n=5`, confirm/deny → the memory reweights, and the next suggestion is measurably more *you*.

ChatGPT is a brilliant stranger every session. Sprout is the same brain that's known you for months — with your private numbers, a compounding weighted memory, proactivity (Telegram nudges), and tools that act on your world.

**Three moats:**

1. Your private analytics (retention, CTR, impressions — data ChatGPT can never have)
2. A live niche graph with per-competitor baselines (not raw view counts)
3. Memory that compounds via Cognee's `remember` / `recall` / `improve` / `forget`

---

## What it does

### The genre reveal
No niche dropdown. After OAuth, Sprout reads your last ~40 videos and tells you what you're actually making — weighted by what *converts*, not frequency:

> *"Your last 40 videos are really three things: slow-living vlogs, self-improvement essays, and personal storytelling — and it's the vulnerable ones that actually grow you. Right?"*

Confirm or correct. The garden paints itself to match your fingerprint.

### Cited concept cards
The killer query is an orchestrated graph join — your converting topics × live trends × true competitors (0.3×–10× your size, ranked by outlier score vs. each channel's own baseline) — not a single vector `search()`. Every card carries receipts: your videos, competitor proof, pattern nodes with sample sizes.

### One-tap teaching
Every suggestion is built from a known trace (Topic + Hook + Format + PatternNodes). Tap **nailed it** / **not me** → `improve()` reweights exactly those nodes. Reject two Shorts cards and the next batch skews long-form. Visible, immediate, no feedback paragraphs.

### Vision board lifecycle
- **Seeds** — passing mentions auto-captured silently into a low-visibility tray
- **Planted** — user-confirmed ideas with painted concept art on the board
- **Sprouted** — posted videos; the card blooms and the Hook+Format+Topic trace gets a positive bump from reality itself

Unplanted seeds compost after a few weeks (`forget()`). Stale trends decay nightly.

### Proactive, earned nudges
Telegram (or the dashboard) delivers good news inside your interruption budget — *"your last video beat your median retention 🎉"* — so you never open Studio just to check. Silence when nothing is earned is a feature.

### Temporal holdout backtest (demo)
The graph is blind to everything after **2026-04-01**, recommends from pre-cutoff patterns, then reveals the actual held-out videos the creator went on to make. Side-by-side RAG contrast included.

---

## Architecture

```
YouTube Data API + Analytics API (OAuth)     Demo fixture (world.py)
         │                                              │
         ▼                                              ▼
   .cache/  ← transcripts, extractions, thumbnails, concept art
         │
         ▼
   Analytics table (pandas)  ← ALL math: CTR, retention, correlations, n
         │
         ▼
   Cognee graph + pgvector  ← PatternNodes, node_sets, feedback weights
   (my_channel / competitors / trends / drafts)
         │
         ▼
   Agent (frontier model + tools)  ← context pack every turn
         │
         ▼
   Next.js garden + Telegram bot
         ▲
   Cron refresh — analytics, trends, forget, compost, nudges
```

**Division of labor:**

| Layer | Role |
|---|---|
| **LLM** (`gpt-4o-mini`, batch) | Categorical labels: topics, hooks, formats, beats. Never arithmetic. |
| **Vision** | Static thumbnail packaging analysis (one cached call/video). |
| **Python / pandas** | All numbers: effect sizes, rankings, confidence tiers. |
| **Cognee** | Memory + join: store, retrieve, reweight, forget. Does not invent patterns. |

**Multi-user (production):** Firebase identity + separate Google OAuth for YouTube Analytics. App state in Cloud SQL `sprout_app`; Cognee graph + vectors in per-user dataset DBs on the same instance. Up to 10 concurrent creators.

**Local dev:** SQLite app state + embedded Kuzu graph under `backend/.cognee/`. Stop uvicorn before ingest (Kuzu is single-writer).

---

## Tech stack

| Piece | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Cognee 1.2.2 |
| Frontend | Next.js 16, React 19, Tailwind v4 |
| Graph + vectors | Postgres + pgvector (prod) · Kuzu + LanceDB (local) |
| App state | SQLModel · Postgres (prod) · SQLite (local) |
| Auth | Firebase (identity) + Google OAuth (YouTube Analytics) |
| LLM | OpenAI `gpt-4o-mini` (batch) · frontier model (chat) |
| Deploy | Cloud Run + Cloud SQL · GitHub Actions |
| Proactive | Telegram bot (per-user deep link) |

---

## Quick start (local)

### Prerequisites

- Python 3.11+
- Node.js 20+
- OpenAI API key
- YouTube Data API v3 key

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_ORG/cognee-hackathon.git
cd cognee-hackathon

cp .env.example .env
# Fill in LLM_API_KEY and YOUTUBE_API_KEY

cp frontend/.env.local.example frontend/.env.local
# Firebase keys optional — without them, /studio demo mode still works
```

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
python -m memory_shield.corpus          # fetch @LanaBlakely corpus → .cache/
python -m memory_shield.ingest --fresh  # stop uvicorn first if re-running
uvicorn memory_shield.api:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000/studio](http://localhost:3000/studio) for the demo path, or [http://localhost:3000/signup](http://localhost:3000/signup) for the real OAuth flow (requires Firebase + Google OAuth setup — see [.github/SIGNIN_SETUP.md](.github/SIGNIN_SETUP.md)).

### Optional: local dev against Cloud SQL

```bash
export SPROUT_DATABASE_URL=postgresql+asyncpg://postgres:PASS@HOST:5432/sprout_app
export DB_HOST=HOST DB_PASSWORD=PASS DB_NAME=cognee_meta
# Cognee switches to postgres+pgvector automatically
```

Verify Postgres + Cognee isolation:

```bash
python -m memory_shield.scripts.phase0_smoke
```

---

## Environment variables

### Root `.env`

| Key | Required | Purpose |
|---|---|---|
| `LLM_API_KEY` | Yes | OpenAI — Cognee extraction + embeddings + agent |
| `YOUTUBE_API_KEY` | Yes | YouTube Data API (corpus, live stats, competitors) |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | Real users | YouTube Analytics OAuth |
| `GOOGLE_OAUTH_REDIRECT_URI` | Real users | Default: `https://api.sprout.asad.codes/auth/youtube/callback` |
| `TELEGRAM_BOT_TOKEN` | Optional | Proactive nudges via Telegram |
| `TELEGRAM_LINK_SECRET` | Optional | HMAC for per-user Telegram deep links |
| `SPROUT_DATABASE_URL` | Prod | Postgres app state (unset → SQLite local) |
| `DB_HOST/PORT/USERNAME/PASSWORD/NAME` | Prod | Cognee meta DB (`cognee_meta`) |
| `FIREBASE_*` / `FIREBASE_SERVICE_ACCOUNT_FILE` | Real users | Firebase Admin token verification |
| `FRONTEND_URL`, `CORS_ORIGINS` | Prod | OAuth redirects + CORS |
| `CRON_SECRET` | Prod | Protects `/internal/cron/*` endpoints |
| `CREATOR_HANDLE` | Demo | Default `@LanaBlakely` |

### Frontend `frontend/.env.local`

| Key | Purpose |
|---|---|
| `NEXT_PUBLIC_FIREBASE_*` | Firebase Auth config |
| `NEXT_PUBLIC_API_BASE` | Backend URL (default `http://localhost:8000`) |

See [`.env.example`](.env.example) and [`frontend/.env.local.example`](frontend/.env.local.example) for templates.

---

## Project layout

```
cognee-hackathon/
├── backend/memory_shield/     # FastAPI app, Cognee pipeline, agent
│   ├── api.py                 # REST endpoints
│   ├── agent.py               # Chat agent + tool registry
│   ├── recall.py              # Killer query + gap-finder
│   ├── ingest.py              # Two-lane Cognee ingest
│   ├── analyzer.py            # Pattern computation (pandas)
│   ├── onboarding.py          # Real-user channel setup
│   ├── refresh.py             # Background cron refresh
│   ├── db/                    # SQLModel schema + repos
│   └── auth/                  # Firebase + YouTube OAuth
├── frontend/                  # Next.js garden UI
│   ├── app/studio/            # Demo dashboard
│   ├── app/signup/            # Real-user onboarding
│   └── components/            # IdeasBoard, ProductionKit, etc.
├── scripts/                   # GCP provision + deploy
├── .github/workflows/         # CI + Cloud Run deploy
├── CLAUDE.md                  # Authoritative build spec (for agents)
├── DESIGN.md                  # Human-readable product + mechanics explainer
└── DEMO_SCRIPT.md             # 90-second judge demo script
```

---

## Cognee integration

Sprout is built around Cognee's four ops — not as decoration, but as the product loop:

| Op | What Sprout does with it |
|---|---|
| **`remember`** | Two-lane ingest: Lane A (deterministic skeleton + PatternNodes) + Lane B (`cognify` on transcripts). Scoped `node_set`s: `my_channel`, `competitors`, `trends`, `drafts`. |
| **`recall`** | Hand-orchestrated multi-step retrieval — your patterns × trends × competitors → cited concept cards. Semantic topic matching via vector neighbors + one graph hop. |
| **`improve`** | One-tap feedback → native `feedback_weight` bumps on the exact nodes behind each suggestion. Pattern confirm/deny. Posted-video positive signal. |
| **`forget`** | Trend dataset decay (`trends_YYYY_wWW`), seed compost, explicit "never suggest again" + durable exclusion nodes. |

**Why not plain RAG?** Three places the graph earns its keep:

1. **The join** — multi-hop traversal across node sets (your converting topics → competitor videos → filtered creators). Vector search returns similar text; Sprout returns *actionable, niche-scoped, baseline-ranked* cards.
2. **The anti-join** — gap-finder: trending topics near your fingerprint with *no* path to topics you already cover. Set-difference, not similarity.
3. **Weighted learning** — feedback numerically reweights nodes; the next retrieval reads those weights. Sharper, not bigger.

---

## Deployment

Production runs on **GCP Cloud Run + Cloud SQL Postgres** (`sprout-cognee-hackathon`, `us-central1`).

```bash
./scripts/gcp-provision-sql.sh      # Cloud SQL + databases (once)
./scripts/bootstrap-gcp-secrets.sh  # .env → Secret Manager (once)
./scripts/setup-github-wif.sh       # GitHub Actions auth (once)
# Push to main → auto-deploy, or: ./scripts/gcp-deploy.sh
```

Full guide: [.github/DEPLOY.md](.github/DEPLOY.md) · Sign-in setup: [.github/SIGNIN_SETUP.md](.github/SIGNIN_SETUP.md)

Legacy VM fallback (`35.193.172.43`) remains until custom-domain smoke test passes.

---

## Demo script (90 seconds)

1. **Hook** — "Memory that gets sharper, not just bigger."
2. **Proof strip** — Citation thumbnails on a concept card. "Your video at 2.2× median + competitor proof."
3. **Graph drawer** — Trend → Topic → Video → Format path behind a card.
4. **Skeptic stack** — RAG contrast → sealed backtest → reveal held-out winners.
5. **Workflow** — Plan it → Board → shoot brief → copy film kit.
6. **Close** — "Post it — memory sharpens from your uploads automatically."

Full script: [DEMO_SCRIPT.md](DEMO_SCRIPT.md)

---

## Documentation

| Doc | Audience | Contents |
|---|---|---|
| [DESIGN.md](DESIGN.md) | Humans | Full product story, mechanics, architecture |
| [CLAUDE.md](CLAUDE.md) | Agents / builders | Terse build spec, env, Cognee API facts, cut-lines |
| [BUILD.md](BUILD.md) | Builders | Snapshot of what's real vs. stubbed |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Presenters | Judge demo walkthrough |

---

## License

Hackathon submission — see repository for license terms.

# IMPROVEMENTS.md — Cursor work plan for Sprout (Jul 5 multi-user build)

**To the coding agent:** Read [`CLAUDE.md`](CLAUDE.md) first. Python package: **`backend/memory_shield/`** only (no root `memory_shield/` folder). Run from `backend/`. Do epics **in order**; keep demo (`uid=demo`) green after each.

---

## Repo layout

```
cognee-hackathon/
├── backend/memory_shield/   # FastAPI + Cognee pipeline (import: memory_shield.*)
├── frontend/                # Next.js studio
├── scripts/                 # gcp-provision-sql.sh, gcp-deploy.sh
├── .env                     # repo root
└── CLAUDE.md, IMPROVEMENTS.md, DESIGN.md
```

---

## Architecture — three stores

| Store | Database | What's in it |
|-------|----------|--------------|
| **sprout_app** | `SPROUT_DATABASE_URL` (Postgres) or `backend/.cache/sprout_app.db` (SQLite) | Users, drafts, analytics_videos, preferences, fingerprints — [`db/models.py`](backend/memory_shield/db/models.py) |
| **cognee_meta** | `DB_NAME=cognee_meta` on same Cloud SQL instance | Cognee user/dataset registry |
| **Per-user datasets** | `sprout_{uid}` DBs (max 10) | Graph + pgvector; isolated via [`user_cognee_context()`](backend/memory_shield/cognee_context.py) |

**Two-store discipline:** All math in `analytics_videos` (pandas). Only pattern nodes, episodes, weights go to Cognee graph.

**Local dev:** No `SPROUT_DATABASE_URL` → SQLite + kuzu under `backend/.cognee/`. Stop uvicorn before `python -m memory_shield.ingest`.

---

## sprout_app schema (current)

Initialized via `SQLModel.metadata.create_all()` in [`api.py`](backend/memory_shield/api.py) lifespan — **no Alembic**. Phase 0 adds `ensure_schema()` for `ALTER TABLE` on existing DBs.

| Table | Key fields |
|-------|------------|
| `users` | `uid` PK, `cognee_user_id`, `cognee_dataset_id`, `telegram_chat_id`, `onboarding_*`, `is_demo` |
| `oauth_credentials` | encrypted tokens per uid |
| `preferences` | `interruption_budget`, `competitor_exclusions` |
| `drafts` | `state` (seed/planted/sprouted), `sprouted_video_id` — **missing `payload`, `target_date`, `episode_id`** |
| `analytics_meta` + `analytics_videos` | uid-scoped metrics; `ratio_vs_baseline`, `growth_score`, retention |
| `fingerprints` | genre JSON `payload` |
| `video_stats_snapshots` | live view polls |
| `telegram_poll_state` | global bot offset |

### Planned (Phase 0 + Epic 1)

- **`drafts`:** add `payload` JSON, `target_date`, `episode_id`
- **`suggestion_episodes`:** new table — suggestion → decision → outcome chain (source of truth for Epic 2 self-audit)
- **Epic 6:** `preferences.competitor_alerts`

---

## Cognee graph schema (current)

[`graph_models.py`](backend/memory_shield/graph_models.py): `Creator`, `Topic`, `Hook`, `Format`, `Video`, `Trend`, `PatternNode`, `Draft`, `Preference`, `CommentTheme`.

**node_sets:** `my_channel`, `competitors`, `trends`, `drafts`.

**Planned Epic 1:** `SuggestionEpisodeNode` + `episodes` node_set (graph mirror of SQL episodes).

**Naming:** SQL `drafts` table ≠ Cognee `Draft` DataPoint.

**No Cypher in prod** — aggregates via [`kg.Graph`](backend/memory_shield/kg.py) loader (`gap_finder` pattern).

---

## Legacy JSON caches (`backend/.cache/`)

Still mirrored for local dev; **new features write to SQL only.**

| File | Note |
|------|------|
| `corpus.json` | Global — demo OK |
| `analytics.json` | Mirror; DB is authoritative per uid |
| `track.json` | **Global, not uid-scoped** — do not use for episode outcomes; use `analytics_videos` |
| `drafts.json` | Stale; drafts are in SQL |

---

## Global rules (every epic)

- Every Cognee op inside `user_cognee_context(dataset_id, user_id)`
- Never wipe global graph in multi-user paths
- Computed numbers only; encouragement framing
- Map work to Creator Moments in CLAUDE.md

---

## Epic order

1. **Episodic memory** — `suggestion_episodes` + write threading (→ M4)
2. **Self-audit recall** — `advice_track_record()` (→ M4 UI)
3. **Temporal trajectory** (→ M6)
4. **memify consolidation** — MetaPattern (→ thesis)
5. **Production kit** (→ M5)
6. **Competitor calm + Telegram** (→ M2, M8)
7. **Demo focus + GenreReveal** (→ M1)

Full implementation plan: `.cursor/plans/creator_moments_+_telegram_fa62d286.plan.md`

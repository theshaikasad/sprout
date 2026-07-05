# IMPROVEMENTS.md — Cursor work plan for Sprout (revised for the Jul 5 multi-user build)

**To the coding agent:** You are working in the existing `memory_shield` repo. `@CLAUDE.md` is the authoritative build spec — read it first; do not contradict it. This file adds seven epics that close real product + memory gaps. Do them **in order** (later epics depend on earlier ones), keep the app deployable after each, and **never break the demo path**. This revision is aligned to the current architecture: **Cloud Run + Cloud SQL Postgres/pgvector, multi-user (10 cap), per-user Cognee isolation, OAuth shipped.**

## Global rules (apply to every epic)

- **Per-user Cognee isolation is non-negotiable.** Every Cognee op runs inside `user_cognee_context(dataset_id, user_id)` from `cognee_context.py`.
- **No raw Cypher in production paths.** Graph traversal = Python aggregation over in-memory `Graph` loader (`gap_finder()` precedent).
- **Two-store discipline.** Math in `analytics_videos` / pandas; only results in Cognee.
- **App state is uid-scoped SQLModel** in `db/models.py`.
- **Preserve the demo.** `uid=demo`, `HOLDOUT_CUTOFF=2026-04-01`, backtest + RAG contrast after every epic.
- **Map work to the eight Creator Moments in `@CLAUDE.md`.**

## Epic order

1. **Episodic memory** — suggestion → outcome chain (→ M4)
2. **Self-audit recall** — memory grades its own advice (→ M4)
3. **Temporal trajectory** (→ M6)
4. **memify consolidation** — MetaPattern rules
5. **Production kit** (→ M5)
6. **Competitor calm + Telegram** (→ M2, M8)
7. **Honest degradation + demo focus** (→ M1)

See the full epic specifications in the project plan and `@CLAUDE.md` Creator Moments section.

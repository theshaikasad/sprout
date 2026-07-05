# BUILD.md — current state of the Sprout build

Snapshot as of **Jul 5 2026** (hackathon submission day). `CLAUDE.md` is still the spec; this is the "what actually exists and works right now" log.

## Live deployment

- **App:** http://35.193.172.43:3000
- **API:** http://35.193.172.43:8000
- **GCP project:** `sprout-cognee-hackathon` (billing account `01EC03-1F075F-E9C85F`)
- **VM:** `sprout-vm`, us-central1-a, e2-medium, static IP `35.193.172.43`
- Both backend (`sprout-backend.service`) and frontend (`sprout-frontend.service`) run as systemd services — auto-restart on crash, survive reboot.
- **Why a VM, not Cloud Run:** Cognee's kuzu graph store needs real POSIX file locks (`flock`-style single-writer semantics, confirmed directly — "Could not set lock on file" errors when two processes touched the graph at once). Cloud Run's ephemeral/GCS-FUSE storage can't guarantee this, and it can silently scale to multiple instances unless pinned to 1, which would corrupt the single-writer assumption. A persistent VM matches the app's actual architecture; Cloud Run + Filestore would work too but costs ~$200+/mo for a hackathon demo.
- **Redeploy:** `tar` the repo (excluding `.venv`, `node_modules`, `.next`, `.git`), `scp` to `~/sprout` on the VM, `pip install -r backend/requirements.txt` / `npm install && npm run build`, `sudo systemctl restart sprout-backend sprout-frontend`.

## What's real vs. what's flagged/stubbed

| Piece | Status |
|---|---|
| Two-lane ingest, PatternNodes, `exhibits` edges | **Real**, ingested (581+ nodes, 1000+ edges) |
| Genre fingerprint + competitor triangulation | **Real**, computed from actual corpus |
| Killer query (`recall.py`) | **Real**, cited cards, anti-slop gates verified |
| Anti-join gap-finder | **Real** — literal Cypher `NOT EXISTS`, tested against live graph, exposed in `/gaps` + the RAG-contrast panel |
| One-tap feedback (`improve()`) | **Real** — verified weight changes propagate to the next `/suggest` |
| `confirm_pattern` | **Real** (was a stub earlier today — resolved to actual PatternNode + reweights its real evidence trail) |
| Seeds → planted → sprouted board | **Real**, JSON-backed, `mark_sprouted` now genuinely reweights graph nodes |
| Preferences (`set_preference`, `remove_competitor`) | **Real** — writes actual `Preference` DataPoints, not just a JSON cache (this was entirely missing before today) |
| Telegram bot | **Real** — send + poll both confirmed live against a real Telegram chat |
| Concept art | **Real** — `gpt-image-1` (dall-e-3 is retired), static-served, rendered in the UI |
| Cron / background refresh | **Real** — in-process asyncio loop, hourly, verified via `digest.json` updating on schedule |
| Temporal-holdout backtest | **Real** — correctly names the actual held-out videos |
| OAuth (real path) | **Code-complete** (token exchange + channel confirm), consent screen not yet configured — see below |
| Transcripts | **Partial** — 22/128 videos (YouTube IP-blocked mid-fetch twice); Lane B semantic search and Pacing patterns are correspondingly degraded |
| Discourse radar | **Degraded, not broken** — Reddit blocked (403) on this network, HN-only fallback works but low topical fit for this niche |

## Known bugs found + fixed this session

- Stale pre-pivot `suggest` cache was serving old Shawhin/Dev-AI content
- The "memory gets sharper" re-rank was silently broken by that same cache (fixed + added retry-on-empty-LLM-sample resilience)
- `workspace.py`'s reconnect-reset was clearing the wrong file (dead `ideas.py`'s path, not the real board)
- A destructive stale demo-channel link on `/signup` still pointed at `@ShawhinTalebi` and would have triggered a full `fresh=True` re-ingest, wiping the whole graph — neutralized

## Not done / deliberately deferred

- **Google OAuth consent screen + client ID** — requires the Cloud Console UI and your identity (test users, support email). Instructions given separately; once you send me the Client ID/Secret, wiring them in is a one-line `.env` change + restart.
- **GCP budget alert** — attempted via CLI, hit a persistent `INVALID_ARGUMENT` I didn't chase down. Takes ~30s manually at console.cloud.google.com/billing → Budgets & alerts.
- **Full transcript backfill** — YouTube's IP block hadn't lifted after two attempts; re-running `python -m memory_shield.corpus` later should pick up where it left off.
- **HTTPS / custom domain** — currently plain HTTP on a bare IP; fine for a demo link, not for anything longer-lived.

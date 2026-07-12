# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repo. This file is the **authoritative source of truth** (the old `memory_shield_system_design.md` was deleted in the Jul 3–4 pivot).

## Project status

**Pivoted Jul 3–4 2026** from "Memory Shield" (a content-strategist that *pushed* advice) to **a quiet creator companion with a memory of you** — product name **Sprout** (code/package stays `memory_shield`). WeMakeDevs × Cognee hackathon ("The Hangover").

**Jul 5 2026 — multi-user Postgres on GCP + hackathon submission:** migrated to Cloud Run + Cloud SQL Postgres; custom domains live; GitHub Actions deploy via WIF. The per-user Cognee graph on Cloud SQL never worked on Cloud Run — submission-night prod served pre-built JSON behind fallback shims.

**Jul 12 2026 — repurposed as a resume/portfolio demo (current mission):** the hackathon is over and the product is not being pursued. Prod was re-architected to run **the mode that actually works — single-tenant kuzu/lancedb ("local mode") — with the frozen demo world baked into the Docker image** (`backend/demo_graph/` = `.cognee` snapshot, `backend/demo_seed/` = `.cache` snapshot, both committed to git; rebuild via `./scripts/snapshot-demo-world.sh`). The fallback-shim layer and the false "Cloud Run can't reach OpenAI" Lane-B skip were deleted. Everything the local demo does now runs live in prod: graph, suggest (3 cited cards), gaps, contrast (real DocumentChunks), backtest reveal, `improve()` reweighting, chat agent.

**Why the pivot:** the old thing felt like slop for two structural reasons — it *pushed* generic advice instead of *learning* the creator, and "public Data API only" meant it could never see *why* a video converted. Both reversed: an agent that quietly learns you **+ real YouTube Analytics via OAuth**.

## Current deployment (Jul 12 2026 — portfolio demo)

| Piece | Status |
|---|---|
| **Frontend** | https://sprout.asad.codes — landing CTA → `/studio` (sign-in demoted: Firebase never configured for the custom domain) |
| **Backend** | https://api.sprout.asad.codes — Cloud Run, **single-tenant demo mode**: no `SPROUT_DATABASE_URL`, kuzu store in-image, `min-instances=1`, `max-instances=1` (kuzu single-writer), `CHAT_MODEL=gpt-4o-mini`, per-IP rate limit on `/chat` |
| **Database** | **None attached in prod.** Cloud SQL `sprout-db` still exists (user chose to keep it + `sprout-vm`) but is out of the serving path |
| **Demo clock** | Frozen via `demo_today()` in `corpus.py` (cadence/garden/track/nudges) — the fixture never reads as an abandoned channel |
| **Secrets** | GCP Secret Manager → Cloud Run `--set-secrets` (DB secrets no longer mounted) |
| **CI/CD** | push to `main` → `.github/workflows/ci.yml` + `deploy.yml` (WIF → `github-deployer` SA) |
| **GCP project** | `sprout-cognee-hackathon` · region `us-central1` |

**Telegram:** backend bot code still runs in prod ("use whatever's working"), but the connect tile was removed from the studio UI. HTTP 409 if both local uvicorn and Cloud Run poll the same bot token.

### Deploy pipeline

1. **One-time:** `./scripts/bootstrap-gcp-secrets.sh`, `./scripts/setup-github-wif.sh`, `./scripts/grant-github-deployer-iam.sh`.
2. **Routine:** push to `main` → CI → Deploy (async `gcloud builds submit` + poll; image tag `:latest`).
3. **Manual fallback:** `./scripts/gcp-deploy.sh`.
4. **Demo world refresh (rare):** stop uvicorn → `python -m memory_shield.corpus` → `python -m memory_shield.ingest --fresh` → start uvicorn and warm `/suggest` `/backtest` `/track` → `./scripts/snapshot-demo-world.sh` → commit `demo_graph/` + `demo_seed/`. `backend/.gcloudignore` keeps local runtime stores out of the build context while letting the snapshots through.

**Phase 0 gate (multi-user mode only):** `python -m memory_shield.scripts.phase0_smoke` (requires `SPROUT_DATABASE_URL` + `DB_*` pointing at Postgres).

## Thesis (pitch spine — drives "Best Use of Cognee" + "Creativity")

Lead with **"memory that gets *sharper*, not just bigger"** — Cognee's own thesis (they brand as *"memory for AI agents"*). A companion with a **persistent, improving memory of one creator** — not "RAG + a dashboard," not a "content-idea generator" (crowded slop lane). Every suggestion is **falsifiable and cited** to the creator's real videos/metrics. Product promise: **create more, consume less** — the agent does the doomscroll-research so the creator doesn't, and gives them a calm, encouraging place to look at their vision instead of chronically checking views.

## Creator moments (the litmus test — judge-value vs creator-value)

**The test for every moment:** would the creator tell a friend about it? If a capability can't be phrased as a moment that passes that test, it's judge-value, not creator-value. Build and demo to these eight — not feature lists.

**Through-line (the painkiller loop):** decide (M3) → make (M5) → outcome detected → retro (M4) → refined suggestions (M7). That tightness is what makes the memory feel alive.

1. **"It read me instead of asking."** (onboarding) — One click, Sign in with YouTube. No dropdown, no questionnaire. ~90 seconds later: *"Your last 40 videos are really three things — slow-living vlogs, self-improvement essays, and personal storytelling. And it's the vulnerable ones that actually grow you. Right?"* She confirms. The garden paints itself to match her. → genre fingerprint, the "it gets me" beat.

2. **"It brought me good news so I didn't have to go check."** (proactive, earned) — A Telegram message, unprompted, inside her interruption budget: *"your last video beat your median retention — the personal ones keep doing this."* She never opened Studio. → create-more-consume-less; the anti-stats-casino promise.

3. **"No blank page."** (the Monday ritual) — She opens the garden. Three cited concept cards are already there — each with a hook, a format, and receipts (her videos + a true-competitor video, ranked against that channel's own baseline, not raw views). She reacts; she doesn't compose. → the killer join, react-don't-compose.

4. **"It remembered what I tried, and learned from it."** (THE payoff — the retro) — *"Three weeks ago I nudged you toward the vulnerable essay. You made it. CTR was 1.4× your median and retention held past 2:30 where your setups usually bleed — so demos-early is working for you. I've stopped suggesting listicles; you've passed on the last three."* The single moment that makes the memory feel alive. → idea→outcome episode chain + self-audit, surfaced as a felt moment.

5. **"It didn't stop before the hard part."** (production) — She plants an idea. Beneath the painted card: a script skeleton with a cold-open (her +15% hook pattern), the demo pulled early (demos hold for her), intro kept under 40s (over 40s bleeds), each beat citing the pattern behind it — plus a thumbnail brief in her top-CTR pattern (face + ≤3-word overlay, two text options). She films tonight instead of staring. → beats×retention as output, not just analysis.

6. **"It told me who I'm becoming."** (trajectory) — *"Six months ago you were mostly vlogs. You've been drifting toward personal essays and they convert 3× — that's the direction. Lean in."* Framed forward, never as decline. → fingerprint drift over time (`TEMPORAL` / temporal_cognify).

7. **"I taught it in one tap, and it changed."** (teaching) — She taps "not me" on a shorts-heavy card. The next batch visibly skews long-form. No form, no explaining. → one-tap → `improve()`; sharper, not bigger.

8. **"It knew when to be quiet."** (calm) — Some days it says nothing, because nothing was earned. A competitor's video only reaches her when it maps to an idea she already has — framed as *"good time to make yours,"* never *"they're beating you."* → interruption budget as a feature, not a bug.

**Demo spine:** M1 (onboarding reveal) → M3 (Monday cards) → M4 (retro payoff) → M7 (one-tap skew) is the minimum story arc. M2/M8 prove proactivity discipline; M5/M6 are depth beats if time allows.

## What it is

Sign in with Google (Firebase) → connect YouTube (server-side OAuth, refresh token stored encrypted) → the agent reads your **real analytics** (retention, traffic sources, CTR/impressions, subs-gained, audience, best-time-to-post) and **tells you your own genre** ("your last 40 videos are really X/Y/Z, and Y is what converts — right?") instead of asking you to pick a niche. It builds **one Cognee memory of you** (isolated per-user dataset), then joins *what converts for you* × *live niche trends* × *your true competitors* → **cited concept cards** you steer (theme / duration / optional topic), all the way down to **generated title + description + thumbnail-image concept**, each element citing the validated pattern it applies. It captures every idea you mention into a **vision-board of drafts** (each with AI concept-art), quietly transitions a draft to done when you post it, and **nudges consistency via Telegram** — warm, grounded, never bombarding.

**Demo path unchanged:** `uid=demo`, `is_demo=true` — uses `analytics_fixture.py` + `@LanaBlakely` corpus; no OAuth required. **`/studio` without sign-in.** Prod runs the same kuzu world as local (baked into the image), so the full graph story works at https://sprout.asad.codes/studio.

## The feel — an encouraging space, "old-anime comforting" (load-bearing, not decoration)

The whole product is the **anti-YouTube-Studio**: a calm creative home, not a stats casino. This frame recolors every surface.

- **Aesthetic:** old-anime, comforting — **Ghibli-cozy**: warm hand-painted backgrounds, soft daylight, wood/paper/plant textures; concept-art reads like storybook gouache. NOT a sharp SaaS dashboard — the paintings and warm palette *are* the brand.
- **Name = Sprout → the growth metaphor IS the information architecture (build the frontend around it):** the idea lifecycle **seed → planted → sprouted** is the product's core object model *and* its UI. **Seeds** = passing mentions auto-captured into a low-visibility **seed tray** (small, unadorned, skimmable — deliberately humble so the board never clutters). **Planted** = user-confirmed ideas on the vision-board proper, each with its painted concept-art (the moment of commitment gets the ceremony: planting animation, the card "takes root"). **Sprouted** = posted (the card blooms/bears fruit, then settles into a visible history of growth — the garden remembers what you grew). **Consistency = the garden's overall flourishing** (a gentle visual of tending — never a guilt streak-counter). Every frontend surface should answer to this metaphor: copy ("plant it?", "4 seeds this week", "composted"), iconography, transitions, empty states ("nothing planted yet — got a seed?"). A dashboard *shows numbers*; Sprout *shows a garden growing* — numbers only appear as receipts behind cards.
- **The board's background = your genre fingerprint made visible:** one clean, aesthetic painted backdrop generated from the channel's theme (Dev/AI → cozy painted study, warm lamplight; cooking → sunlit kitchen garden). Generated **once at onboarding** — right after the "here's your genre" reveal, the garden *paints itself to match you* (the "it gets me" beat made visual) — cached forever; regenerate only on explicit refresh or major fingerprint drift. Must stay **atmospheric**: soft, low-contrast, desaturated wash so cards stay legible. Zero-cost fallback: a hand-picked default Ghibli-cozy painting.
- **Home surface = consistency + waiting ideas** (decided). What greets the user: how consistent they've been (a gentle streak/momentum, never guilt) + their vision-board of ideas waiting. Analytics live *underneath*, surfaced only as encouragement or as a receipt behind a suggestion. No view-counter on the home screen.
- **Every metric reframed as encouragement + next action, never anxiety.** Canonical example — high CTR, low retention → *not* "your retention is bad" but *"People are clicking — your packaging is landing, that's the hard part. They slip around 0:40; want two ways to hold them?"* Every weakness = "you already won X; here's the next unlock."
- **The agent brings good news to you** ("your last one beat your median retention 🎉") so the user never goes to YouTube to *check*.

## The core loop (this IS the product = the four Cognee ops)

> your analytics → distilled into a memory of you → research tools query that memory + the live niche → earned, cited nudges/cards in chat → your one-tap reaction → `improve()`/`forget()` → sharper memory → repeat.

Litmus test for every feature: **could ChatGPT do this in a chat window right now?** If yes, cut it. Second test: **does it land as a creator moment?** (see above — judge-value vs creator-value). Our three moats: (1) your private numbers, (2) a live niche graph with per-competitor baselines, (3) memory that compounds. Also: if a feature doesn't make the cross-`node_set` **join** stronger (only wider), cut it.

**Positioning vs frontier chat apps (the "why not just ChatGPT?" answer):** we don't compete with frontier models — **we arm one.** User-facing chat + final phrasing run on a frontier model via API (affordable: chat is low-volume; cost discipline lives in the batch pipeline, which stays on `gpt-4o-mini`). Same brain, plus what it can't have in ChatGPT's window: your private numbers (no paste-your-analytics ritual), a compounding weighted memory, proactivity (ChatGPT never texts first), tools that act on your world, and a calm place. Honest concession: generic questions are a tie — **Sprout wins every prompt containing "my."** Pitch line: *"ChatGPT is a brilliant stranger every session; Sprout is the same brain that's known you for months."*

## The analysis layer — who does what (foundational)

- **LLM** = turns messy text into clean *categorical labels* + final *phrasing*. Never does arithmetic.
- **Vision model** = same, for images — one call per *static thumbnail*, cached (packaging analysis, NOT video-frame CV).
- **Python (pandas/numpy)** = *all numbers*: retention/CTR comparisons, correlations, effect sizes, ranking. Where "which hook wins" is actually decided.
- **Cognee** = memory + join: stores/links/retrieves nodes, reweights (`improve`/`memify`). Does NOT invent patterns — it remembers the ones we compute.
- Pipeline: **numbers (Analytics API) → features (LLM/vision) → patterns (Python) → nodes (Cognee) → retrieved + reweighted.** When Sprout says "2.1×," it prints a computed field — the LLM never estimates numbers.
- **Who runs it, when (nothing is automatic):** pattern computation is a scheduled **analyzer job** in the refresh pipeline — *not* triggered by the LLM or a chat message. Runs on new-video ingest, on fresh analytics (daily cron), and on-demand (`run_pattern_scan`). At ~60–80 videos it's milliseconds, so we just recompute all patterns each refresh tick.
- **Two stores (don't force stats through the graph):** number-crunching runs over an **analytics table** (videos × features × outcomes, built at ingest) — grouping/correlation is tabular. In production this table lives in **`sprout_app.analytics_videos`** (uid-scoped); locally also mirrored to `.cache/analytics*.json` for demo. Only the *results* (PatternNodes + `exhibits` edges) are written into **Cognee** for retrieval, reweighting, and citation.
- **Batch eagerly, retrieve lazily:** patterns are precomputed in the background; at chat time `recall` only **retrieves** the relevant PatternNodes — no live math in the conversation.

## Cognee = load-bearing (four ops, grounded in REAL data)

- **remember** = two-lane ingest of your channel + **analytics** + trends + competitors into one hybrid graph, scoped by `node_set` (`my_channel` / `competitors` / `trends` / `drafts`); analytics distilled into durable **pattern-nodes** (Hook / Format / Topic-demand / Packaging / Audience / Timing).
- **recall** = the **killer query**: hand-orchestrated multi-step retrieval (your learned patterns × recent Trends × true competitors → LLM synthesizes cited cards). *Not* a single `search()` call — that orchestration is the technical core. Topic matching is **semantic, not keyword**: embed the topic → vector-neighbors + one graph hop → filter to your fingerprint, so "RAG" pulls in "agentic AI" but only toward what you can credibly make.
- **improve / memify** = one-tap feedback + confirmed pattern-hypotheses + posted-video signals bump `feedback_weight` on the Hook+Format+Topic trace → visibly sharper next suggestion ("the Memory Shield effect"). Also handles posted-draft de-weighting (state→done, importance down, out of `drafts` set).
- **forget** = trend decay via scoped `forget()` on dated trend datasets (`trends_YYYY_wWW`), **seed compost** (unplanted seeds expire after a few weeks), and explicit user deletes ("never suggest this again"). *Not* used for posted drafts (those are reweighted, not deleted, to keep idea→outcome for learning).

## The graph update loop (Cognee does NOT auto-update — we orchestrate)

Nothing changes unless we call a Cognee op, so "live memory" = an **explicit, incremental, cron-driven background refresh** (decided):
- **New analytics** (daily cron) → recompute pattern-node deltas → `add_data_points` + `memify` reweight. Only changed videos get re-cognified (cheap).
- **New upload** (poll uploads) → ingest both lanes → embedding-match against open drafts → *propose* clearing one.
- **New trends / competitor posts** (nightly cron) → ingest into `trends`/`competitors` node_sets → `forget` datasets past the decay window.
- **User feedback** (thumbs / confirm-deny) → `remember(FeedbackEntry)` → `improve()`, immediate.
- Incremental + cached + dedup'd. **Production:** Postgres client-server — no file lock; Cognee's per-dataset queue serializes writes to one user's graph. **Local dev (no `SPROUT_DATABASE_URL`):** kuzu single-writer — stop uvicorn before `python -m memory_shield.ingest`. Background refresh runs per-user via `refresh.py` + optional Cloud Scheduler hits on `POST /internal/cron/refresh` and `POST /internal/cron/live-stats` (header `x-cron-secret`).

## Competitor & genre engine (the graph's best argument — "niche" as a label is useless)

Three stages:
1. **Genre = a fingerprint, not a dropdown.** Represent the creator as a weighted distribution over topics × formats derived from their own videos, **weighted by what converts** (analytics). This is a set of embedded Topic nodes in the graph. Emergent, multi-dimensional. Also the onboarding "it gets me" beat (the system tells you your genre).
2. **True competitive set = triangulate, don't label.** Join over: **algorithmic adjacency** (your Analytics "suggested-video" traffic → channels YouTube actually recommends next to you — the gold signal, real path only), **embedding similarity** (topic-fingerprint neighbors — demo-safe), and **search co-occurrence** (who ranks on your converting topics). Filter by a **size band (~0.3×–10× your subs)** — comparing to MrBeast is useless *and* demoralizing (also a kindness rule). In graph terms: `Creator → high-value Topics → other Videos → their Creators (filtered)` = a multi-hop join vector search can't do.
3. **Which of their videos to surface.** Rank by transferable signals, NOT raw views: **outlier score** (views ÷ that channel's own median), **velocity** (views/day since publish), **topic-match** to your convertible topics (tag "in your lane" vs "adjacent/expansion"), and **format you can actually execute**. Honest limit: public API gives competitors' views/likes but never their retention/traffic — we reason from public title/thumbnail/topic/format patterns, and say so.

## Pattern learning & the honest "why" → grounded generation

Nobody (not even the creator) can say *why* with certainty, so we don't claim to:
- **We surface correlations across the creator's own portfolio, with sample size** — "across your 12 tutorials, the 5 with a number in the title averaged 2.1× CTR" — stated as a pattern with `n`, never as causation.
- **Confidence tiering** = the anti-slop guardrail: a pattern only surfaces past a support threshold (enough videos) + effect size. `n=2` is "early signal"; `n=10` consistent is a rule.
- **Full-transcript × retention alignment (deepest signal):** transcripts are timestamped and the retention curve is time-indexed, so we segment each of *your* videos into beats (intro/context/demo/sponsor/CTA/outro) and map beats onto the curve → "demos hold, intros >40s bleed" → pacing/structure PatternNodes. One cached segmentation pass/video; math in Python. Competitors: structure/topics only (no retention for them).
- **Stratify by format-class:** never pool Shorts and long-form when computing patterns — their physics differ (1s hooks, loop-retention, swipe-away). Compute every pattern separately per `is_short`.
- **The human supplies causality:** agent proposes the pattern as a *hypothesis* → creator confirms/denies → `improve()` strengthens or buries it. The memory keeps only *validated* patterns. Machine detects patterns; human judges cause.
- **Generation is constrained by validated patterns, with receipts** — this is how title/description/**thumbnail-concept** drafts avoid being slop: "Title uses your number+outcome pattern (2.1× CTR, 5 vids); thumbnail = face + 3-word overlay (your top-CTR trait); hook = cold-open question (+15% retention)." Not a blank creative prompt — *your* rules applied to *this* idea.
- **Title/description SEO optimizer (two pattern sources + real keywords):** mine (a) *your* validated title/desc patterns (private, from the analyzer) and (b) *trending/niche* title+description patterns (public, **descriptive/weak-label** — recurring keywords, structures, lengths among high-velocity videos; no CTR for them, so no causal claims), then pull (c) the **real search keywords** for the topic (YouTube autocomplete/search + your own Analytics search-traffic terms). Feed all three as **constraints to a strong LLM** to rewrite title/description, then validate (keywords hit? your patterns fit? length ok?) with receipts. "SEO-optimized" = grounded in real search demand + your patterns + current niche structure, not keyword-stuffing.
- **Vs incumbents (vidIQ/TubeBuddy — researched):** they're keyword databases + template generators + grade meters. Their "estimated CTR potential" scores are model-invented numbers from *global* top-performers (the imitate-clickbait trap with a decimal point); no memory — you can't tell vidIQ "that pattern doesn't work for me" and have it remember; keyword-first + gamified 0-100 grades = the stats casino. Our contrast in one line: **they score your title against everyone's videos; Sprout validates it against yours** — computed receipts (`2.1× CTR, n=5`), confirm/deny → `improve()`, conversion-first (growth score), calm rationale instead of a grade meter. (TubeBuddy's thumbnail A/B test is honest but post-publish, ~500 impressions/arm, never accumulates; our analog = mining the natural experiments already in your back catalog.)
- **No fine-tuned model (deliberate).** A clean training set would need `{title/desc → real CTR}`, but CTR is private — you have it only for the signed-in creator's own tens of videos (too few to train) and never for trending videos (views only = weak, confounded). Imitating trending titles also just learns surface clickbait without the context that made them work (= slop). So a strong model *constrained by the pattern layer* beats a small fine-tune here — more controllable, explainable, citeable, faster. **Roadmap:** once many creators have signed in and logged thousands of `{title/desc → real CTR}` rows, a trained scoring model becomes viable — a data-flywheel future, not day-1.

## Research tools (must beat ChatGPT/Claude)

Each fails the "could ChatGPT do it?" test:
1. **Your-performance analyzer** — reads your retention/subs/traffic → "what converts + why." (No data access for ChatGPT.)
2. **Velocity trend radar** — current videos in your *true* niche ranked by views-per-day-since-publish. (Live + quantitative + niche-scoped.)
3. **True-competitor watch** — the graph-found set, monitored vs. each channel's own baseline.
4. **Demand/gap finder — a graph anti-join, not a similarity search.** Trending Topics (velocity-ranked, in `trends`) that sit near your fingerprint via the semantic bridge, filtered to those where **no** path reaches a Topic you already cover. **Production (Postgres graph):** implemented as a **Python anti-join** over the in-memory `Graph` loader (`gap_finder()` in `recall.py`) — Postgres adapter has no raw Cypher. **Local kuzu dev:** can still show literal Cypher in the RAG-contrast panel. The contrast demo describes the equivalent set-difference; product behavior is unchanged. Considered-and-cut: deeper idea-citation chain, cross-competitor pattern corroboration, temporal pattern-decay check.
5. **Memory read/write** — every finding recalls-your-context first, writes back a durable node. The compounding moat.
6. **Discourse radar** — "what's my corner of the internet talking about." X's API is now paid/gated — use the **Reddit API + Hacker News API** (both free); which subreddits = derived from the fingerprint (for the demo niche: r/simpleliving, r/selfimprovement, r/getdisciplined…; HN when the creator is Dev/AI); *cross the discourse against the creator's fingerprint* ("Reddit is buzzing about X; you convert on adjacent Y — here's an angle only you can do"), ranked by fit, cited. Not a generic news digest.

The behavioral pitch (ties to "create more, consume less"): **the research tools replace the creator's own doomscroll-research** — the agent brings the distilled signal so they never open the feed.

## Chat UX & vision-board

- **"React, don't compose."** A blank chatbar makes a tired creator do the hard work; the companion does the articulating and asks for **yes / no / tweak**. First run = onboarding-by-questions (~4, conversational). Steady state = it initiates only when *earned*.
- **Two surfaces, one brain (one Cognee memory):** **Telegram** = ambient / proactive / quick-capture (nudges, competitor alerts, "what are you making?" → one-line reply → saved to drafts) — **a real working bot for the demo, with a scripted fallback prepped** in case it flakes on stage. **Dashboard** = deliberate & visual (the memory made visible, cited cards with real thumbnails, the backtest, the vision-board).
- **The agent has tools that read *and write* the memory (it's not Q&A).** Reads: `get_my_performance` (precomputed PatternNodes + analytics-table slices), `scan_trends` (velocity radar, cached), `check_competitors` (vs their own baselines), `search_discourse` (HN/Reddit cache × fingerprint), `get_drafts`/`get_seeds`, `optimize_title_desc`, `validate_packaging`. Writes: `save_idea` (seed|plant), `edit/mark_done idea`, `add/remove_competitor`, `set_preference`, `set_interruption_budget`, `confirm/reject_pattern`, `run_pattern_scan`/`run_trend_scan`, `snooze_nudges`. Example: "remove @X as a competitor" → pulls X from the `competitors` node_set **and** writes a durable exclusion so nightly auto-discovery never re-adds them. The four Cognee ops are literally exposed as user tools (confirm→`improve`; never-suggest→`forget`+exclusion).
- **When tools fire (four rules):** (1) a **context pack** auto-assembles every turn — preferences/goals, relevant graph recall, board + seed tray, and the cron's "since we last talked" digest (which is how openers carry earned news with zero live work); (2) read-tools fire when the reply needs a fact — hard rule: **the agent may not state a number that didn't come out of a tool**; (3) write-tools fire only on explicit command or a confirmed proposal — **destructive mutations always confirm first**, never silent; (4) reads hit last night's caches; live scans only on explicit "check now" (batch eagerly, retrieve lazily).
- **Every claim cited + one-tap falsifiable** ("nailed it / you're wrong" → `improve()`). Feedback trains *their* memory, visibly, by next message.
- **Cross-session recall** ("last week you wanted a RAG series — a competitor just posted one and it's overperforming; good time?"). **Interruption budget** set in onboarding — silence is part of the anti-bombardment promise.
- **Proactive reminders (three kinds, always encouraging, always within the interruption budget):** *idea-completion* ("finish your RAG video idea — still trending"), *celebration* ("woohoo — your last video is beating your median retention"), and *consistency* ("3-week streak — want to lock a slot?"). Fired by the cron/analyzer (idea staleness, a video beating baseline, a cadence gap), delivered via Telegram/dashboard — never guilt, always good-news or next-step framing.
- **Vision-board = seeds → planted → sprouted (the lifecycle IS the brand, each state = a Cognee op):** passing idea-shaped mentions are **auto-captured as seeds** into a low-visibility seed tray via a silent end-of-turn curation pass (`remember`) — nothing is ever lost, nothing clutters the board, no interruption. The board proper holds only **planted** (user-confirmed) ideas. The agent *asks* to plant only when an idea is concrete (topic + angle + format) — the interruption threshold is idea quality, so each ask feels like a compliment; explicit "save that" plants immediately, no confirmation theater. Unplanted seeds **compost** after a few weeks (real `forget()` — they're seeds, not commitments); periodic gentle tray review ("4 seeds this week — plant any?") within the interruption budget. **Posting = sprouted** (the posted-draft reweight).
- **Multi-message idea capture:** ideas converge over turns, so capture is the agent's job, not a parser's — it has the whole window in context. What's stored is a **distilled card** (title, one-line angle, format, topic links, `derived_from`, provenance pointer to the convo), never raw transcript (chat logs live outside the graph). Before creating, **embedding-match against open drafts/seeds** → update instead of duplicate (same machinery as completion detection).
- **Concept-art on planting only** (painterly, reflects the idea text) — cache **once per planted idea** to disk, behind a feature-flag with a zero-cost fallback (topic-tinted gradient) so it's cuttable if the image bill climbs. **Completion detection:** upload embedding-match → *propose* "did you post this?" (never silent delete; editable); stale-but-unposted ideas get *gently resurfaced*, not deleted; manual "did the pushup one" also works.

## Multi-user architecture (Jul 5 — load-bearing for all new work)

**Auth (two-step, both required for real users):**
1. **Firebase** (`frontend/lib/firebase.ts`) — Google sign-in for identity only; Bearer ID token on every API call.
2. **Google OAuth** (`backend/memory_shield/auth/youtube_oauth.py`) — `GET /auth/youtube/url` → callback stores encrypted **refresh token** in `oauth_credentials`; channel resolved via `channels?mine=true`. No free-text handle input.

**Three logical stores on one Cloud SQL instance:**
1. **`sprout_app`** — SQLModel tables: `users`, `oauth_credentials`, `preferences`, `drafts`, `analytics_*`, `fingerprints`, `video_stats_snapshots`, `telegram_poll_state`
2. **`cognee_meta`** — Cognee relational tables when `ENABLE_BACKEND_ACCESS_CONTROL=true`
3. **Per-user dataset DBs** (max 10) — graph + pgvector, created by `PostgresGraphDatasetDatabaseHandler` + `PGVectorDatasetDatabaseHandler`

**Isolation:** every Cognee op wrapped in `with_user_cognee()` / `user_cognee_context()` (`cognee_context.py`) — including **`Graph.load()`**, `improve()`, `forget_trend()`, `rag_only()`, `topic_distances()`. Auto-provisions Cognee user+dataset on Postgres when IDs missing. Onboarding (`onboarding.py`) creates Cognee user + dataset via `create_user()` + `create_dataset()`, then scoped ingest — **never** global graph wipe. **10-user cap** on new signups (`count_real_users`); demo exempt.

**Cloud SQL unix socket:** Cognee builds `postgresql+asyncpg://user:pass@host:port/db` by default; Cloud Run needs `postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/INSTANCE`. `SPROUT_DATABASE_URL` already uses this; graph/vector dataset engines did not — **`cognee_cloudsql.py`** monkey-patches `_create_graph_engine`, `_create_vector_engine`, and `create_pg_database_if_not_exists` when `DB_HOST` starts with `/cloudsql/` (triggered from `config.py` before `cognee` import). **Prod still failing as of rev 00010 — top post-hackathon fix.**

**Key routes:** `POST /onboarding/start`, `GET /onboarding/status`, `GET /telegram/link`, `POST /connect` (demo-only fast path).

**Telegram:** per-user deep link (`/start link_{hmac_token}`) → stores `telegram_chat_id`; `poll_forever()` in API lifespan routes by chat_id.

**Near-live stats:** `live_stats.py` polls Data API every refresh tick; Analytics API (retention/CTR) via `analytics_youtube.py` on onboarding + daily cron.

## Demo strategy (dual path — decided)

1. **Real path:** Firebase sign-in → YouTube OAuth → per-user onboarding. Analytics API scopes need Google OAuth consent screen test users (≤100, no review).
2. **Live-demo path:** the demo is **not a video** — it's the real system running on a **fixed, fabricated-but-internally-consistent "world"** (a first-class synthetic fixture: sample channel + videos + transcripts + synthesized analytics + competitors + trends + seeded ideas), so the agent can answer *any* plausible question truthfully relative to that world. Synthesized retention/traffic/CTR must be consistent with the channel's real public view counts. Sample channel = **@LanaBlakely** (1.65M, slow-living/self-improvement vlogger — picked Jul 4 from live API data over @ShawhinTalebi and @struthless): ~33 uploads in 2026 H1 mixing Shorts + long-form (feeds the consistency-garden + `is_short`-stratification stories), and her genre is genuinely un-labelable (the fingerprint's best argument). Named fallback: **@struthless** (1.21M, has a 3×–5× "digital-doom" hit run in late 2025–2026).
- **Centerpiece = temporal-holdout backtest** (blind to the creator's last ~3 months → suggests a direction → reveal the real held-out outcome). **HOLDOUT_CUTOFF stays fixed at `2026-04-01`** — Lana's pre-cutoff pattern is loud (personal/vulnerable essays 3–9.5× long-form median: "I woke up deaf" 9.5×, "Almost 30 and single" 5.2×, "He ghosted me" 3.4× — vs habit-listicles/vlogs sub-median), and in the real holdout she made **both videos the pattern predicts**: "Losing my hearing: 2 years later" (best holdout long-form) and "When people ask why I'm still single…" (best holdout short, 1.7×). The reveal = the agent names the exact videos she went on to make. Don't make the cutoff relative.
- ⚠️ **Her channel peaked in 2024, so all-time medians make recent videos look weak → every baseline must be trailing/recency-weighted** (already decided for fingerprint drift; now load-bearing for the backtest ratios and the encouragement framing — never surface a decline story).
- Keep the **side-by-side RAG contrast** (plain vector `search()` vs. the killer join) to neutralize "isn't this just RAG?"
- **Composite "growth score"** = subs-gained (primary) + retention + CTR + watch-time for ranking; keep components **separate for explanation** (the "great CTR, weak retention" story needs the parts visible).

## Surviving architecture (KEEP — reusable across the pivot)

- **Two-lane ingest:** Lane A `add_data_points()` = deterministic skeleton (Creator, Video+metrics, Format, Audio, + analytics pattern-nodes), LLM-free/cheap. Lane B `cognify()` on transcript text = semantic Topic/Hook. One hybrid graph+vector store; `temporal_cognify=True`.
- **Temporal-holdout partition — decide at ingest** (painful to retrofit): pre-cutoff → live graph; post-cutoff → `holdout` dataset excluded from suggestions.
- **Design deltas (deliberate):** per-video extractor returns format+topics+hook in one budgeted `gpt-4o-mini` call, so Lane A writes deterministic `Video→Topic/Hook` edges (killer query never depends on cognify's nondeterministic extraction); Lane B adds semantic depth. `improve()` rides native `set_node_feedback_weights`; recall reads `feedback_weight`.
- **Cost discipline (non-negotiable):** Lane A stays LLM-free; **cache transcripts, format classifications, raw YouTube JSON, analytics, and concept-art images to disk**; `gpt-4o-mini` for extraction/generation. Tight corpus (~60–80 videos).

## Constraints

- **NOW IN:** Firebase identity + **Google OAuth refresh tokens** + **YouTube Analytics API**; **multi-user (10 cap)** on Cloud SQL Postgres; Cloud Run + custom domains; GitHub Actions deploy.
- **PROD MODE:** single-tenant demo (no Cloud SQL attached). The multi-user Postgres path (`cognee_cloudsql.py`, per-user datasets) stays in the codebase but was never made to work on Cloud Run — treat it as designed-not-deployed.
- **Still OUT:** raw *video/frame* analysis, ASR, motion CV → **transcripts + analytics + one static-thumbnail vision call/video** (a deliberate bounded addition, like the OAuth reversal — a single published packaging image, cached; NOT video-frame analysis). No music-recommendation engine (Audio = tracked attribute). **Instagram / Facebook / TikTok = ROADMAP** — researched walls: IG needs Business acct + FB Page + Meta **App Review (2–6 wks)**; TikTok trending-sounds API is **approved-researchers-only**. X/Twitter API is paid/gated (use HN + Reddit). One demo niche (**slow-living/self-improvement vlogger** — switched Jul 4 from Dev/AI; architecture stays niche-agnostic). No billing/teams — single creator per Firebase uid.

## Cognee API facts (verified against installed cognee 1.2.2 — build to these)

- `remember(data, dataset_name=…)` takes `graph_model=` + `node_set=[…]`; `self_improvement` **defaults True** — pass `False` deliberately. Legacy `add()` + `cognify(graph_model=…, temporal_cognify=…)` = Lane B.
- `search()` has 17 modes. ⚠️ **`SearchType.INSIGHTS` does NOT exist** — graph-native modes: `GRAPH_COMPLETION` (default), `TRIPLET_COMPLETION`, `GRAPH_COMPLETION_COT`, `TEMPORAL`, `CYPHER`. Killer query orchestrates *across* modes. **`CYPHER` only works on kuzu/neo4j** — Postgres graph uses Python anti-join for gap-finder in prod.
- Native feedback: `recall()` → QA ids → `remember(FeedbackEntry(qa_id, feedback_score, feedback_text))` → `recall(feedback_influence=0..1)` / `improve(dataset, feedback_alpha=…)`. `DataPoint` natively has `feedback_weight` + `importance_weight` (never redefine). `memify()` = underlying reweight/prune engine.
- Lane A: `from cognee.tasks.storage import add_data_points` after `cognee.low_level.setup()`; `custom_edges=`, `embed_triplets=`.
- `node_set`: `add(..., node_set=[…])` (Lane B); `DataPoint.belongs_to_set: list[str]` (Lane A). Custom DataPoints from `cognee.low_level`; relationship fields `SkipValidation[Any] = None`; `metadata["index_fields"]` marks embedded fields.
- `forget` has no auto-TTL; scope it to **datasets** (dated trend datasets) — confirm exact signature at build.
- **Env — production (`SPROUT_DATABASE_URL` set):** `ENABLE_BACKEND_ACCESS_CONTROL=true`, `GRAPH_DATABASE_PROVIDER=postgres`, `GRAPH_DATASET_DATABASE_HANDLER=postgres_graph`, `VECTOR_DB_PROVIDER=pgvector`, `VECTOR_DATASET_DATABASE_HANDLER=pgvector`, `DB_PROVIDER=postgres`, plus `DB_HOST`/`DB_PORT`/`DB_USERNAME`/`DB_PASSWORD`/`DB_NAME=cognee_meta` and matching `GRAPH_DATABASE_*` / `VECTOR_DB_*` host/port creds (set automatically in `config.py`). Call `create_db_and_tables()` on startup before first `create_user()`.
- **Env — local dev (no `SPROUT_DATABASE_URL`):** `ENABLE_BACKEND_ACCESS_CONTROL=false`; kuzu/lancedb under `backend/.cognee/`; app state in `backend/.cache/sprout_app.db` (SQLite).
- **Always:** `LLM_MODEL=openai/gpt-4o-mini`; **import `memory_shield.config` before `cognee`, always** (`cognee_env.py`).

## Data model

**Cognee graph (`DataPoint` subclasses):** `Creator`, `Topic`, `Hook`, `Format`, `Audio`, `Video` (incl. **`is_short`** + timestamped **beats**), `Trend`, analytics **pattern-nodes** (Hook/Format/Topic-demand/Packaging/Audience/Timing/**Pacing**), + optional `CommentTheme`. Join edges: `Video-covers→Topic`, `Video-uses→Hook`, `Video-has_format→Format`, `Video-by→Creator`, **`Video-exhibits→PatternNode`**, `Idea-derived_from→Trend/Topic`, `Trend~semantic~Topic` bridge.

**App state (`backend/memory_shield/db/models.py`, uid-scoped):** `User` (Firebase uid PK, `cognee_user_id`, `cognee_dataset_id`, channel fields, `onboarding_*`, `telegram_chat_id`, `is_demo`), `OAuthCredentials`, `Preference`, `Draft` (seed/planted/sprouted lifecycle), `AnalyticsMeta`/`AnalyticsVideo`, `Fingerprint`, `VideoStatsSnapshot`, `TelegramPollState`. Access via `UserContext` (`db/context.py`) set by auth middleware on every request.

## Layout & commands

**Layout:**
- `backend/memory_shield/` — FastAPI app, Cognee pipeline, agent
  - `db/` — SQLModel schema, async/sync sessions, repos
  - `auth/` — Firebase Admin, Google OAuth, FastAPI deps
  - `routes_auth.py` — `/auth/youtube/*`, `/onboarding/*`, `/telegram/link`
  - `onboarding.py`, `refresh.py`, `live_stats.py`, `analytics_youtube.py`, `cognee_context.py`, `cognee_cloudsql.py`
  - `db/schema.py` — `ensure_schema()` adds missing columns on existing Cloud SQL DBs at startup
  - `scripts/phase0_smoke.py` — Postgres+Cognee gate test
- `frontend/` — Next.js 16 + Tailwind v4; `lib/api.ts` (Bearer token), `lib/firebase.ts`
- `scripts/` — `gcp-provision-sql.sh`, `bootstrap-gcp-secrets.sh`, `setup-github-wif.sh`, `grant-github-deployer-iam.sh`, `gcp-deploy.sh`
- `DEMO_SCRIPT.md` — 90s judge walkthrough (presenter script)
- `.env` at repo root; `frontend/.env.local` for `NEXT_PUBLIC_*` Firebase keys

**Local dev (SQLite + kuzu fallback):**
```bash
source .venv/bin/activate
cd backend
python -m memory_shield.corpus           # → .cache/corpus.json (cached)
python -m memory_shield.ingest --fresh   # stop uvicorn first (kuzu single-writer)
uvicorn memory_shield.api:app --reload --port 8000
cd frontend && npm run dev               # :3000, API defaults to localhost:8000
```

**Local dev against Cloud SQL (optional):**
```bash
export SPROUT_DATABASE_URL=postgresql+asyncpg://postgres:PASS@HOST:5432/sprout_app
export DB_HOST=HOST DB_PASSWORD=PASS DB_NAME=cognee_meta
# then uvicorn as above — Cognee uses postgres+pgvector, ENABLE_BACKEND_ACCESS_CONTROL=true
```

**Production deploy:**
```bash
./scripts/gcp-provision-sql.sh          # Cloud SQL + databases (once)
./scripts/bootstrap-gcp-secrets.sh      # .env → GCP Secret Manager (once)
./scripts/setup-github-wif.sh           # GitHub Actions auth (once) — see .github/DEPLOY.md
# Then: push to main (auto) or Actions → Deploy → Run workflow
./scripts/gcp-deploy.sh                 # manual fallback (uses Secret Manager)
```

**GitHub Actions:** `.github/workflows/ci.yml` (PR checks), `.github/workflows/deploy.yml` (Cloud Run). Runtime keys mount from **GCP Secret Manager** via `--set-secrets`. GitHub Secrets: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `NEXT_PUBLIC_FIREBASE_*` (frontend build only). See `.github/DEPLOY.md` for IAM troubleshooting.

**Operational rules (learned the hard way):**
- **Local kuzu only:** stop uvicorn before `python -m memory_shield.ingest`. **Production Postgres:** no file lock; Cognee per-dataset queue handles same-user write serialization.
- **Every Cognee call in multi-user paths** must run inside `user_cognee_context()` — onboarding, refresh, agent tools, `improve()`.
- YouTube IP-blocks transcript bursts; `transcripts.py` throttles + circuit-breaks and never caches block-misses. Re-run `python -m memory_shield.corpus` after a block lifts, then re-ingest.
- When chaining verification after a piped command, `set -o pipefail`.
- **Tailwind v4 + next/font gotcha:** reference `var(--font-fraunces), Georgia, serif` directly in custom classes (see `globals.css`).
- **One daylight theme everywhere:** cream paper / olive ink / moss accent; badges over thumbnails use `#f6eedd`, never `text-fg`/`text-dim`.
- **Cloud Run:** `min-instances=1` keeps Telegram poll + refresh loop alive; onboarding can take minutes (`timeout=3600`).
- **`sprout-vm` + Cloud SQL `sprout-db` are kept deliberately** (user's Jul 12 call) even though prod no longer uses either — don't tear down without asking, don't re-wire without asking.
- **GitHub deploy SA** needs `secretAccessor` + `storage.admin` + `serviceusage.serviceUsageConsumer`; verify secrets with `gcloud secrets versions access`, not `secrets describe`.
- **Cloud Build in CI:** use `--async` + status poll — deploy SA cannot stream default build logs.
- **Every graph read path** must use `with_user_cognee()` — missing scope was the original prod 500 after Postgres migration.

**Env keys (repo root `.env`):**
| Key | Purpose |
|---|---|
| `LLM_API_KEY` | OpenAI (required — app won't import without it) |
| `YOUTUBE_API_KEY` | Data API (corpus, live stats) |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | YouTube + Analytics OAuth (real users) |
| `GOOGLE_OAUTH_REDIRECT_URI` | default `https://api.sprout.asad.codes/auth/youtube/callback` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_LINK_SECRET` | Bot + HMAC link tokens |
| `SPROUT_DATABASE_URL` | Postgres app state (unset → SQLite local) |
| `DB_HOST/PORT/USERNAME/PASSWORD/NAME` | Cognee meta DB (`cognee_meta`) |
| `FRONTEND_URL`, `CORS_ORIGINS` | OAuth redirects + CORS |
| `CRON_SECRET` | Protects `/internal/cron/*` |
| `FIREBASE_*` / `GOOGLE_APPLICATION_CREDENTIALS` | Firebase Admin (prod real-user auth) |

**Frontend (`frontend/.env.local`):** `NEXT_PUBLIC_FIREBASE_*`, `NEXT_PUBLIC_API_BASE`.

Python 3.11+. Cognee 1.2.2 self-hosted OSS.

## Build order & cut-lines (updated Jul 12 — portfolio mission)

**The project is now a resume/portfolio demo, not a product** (Asad's Jul 11–12 call after the hackathon). Frame new work as demo-polish or honest documentation, not product growth.

**Shipped:** everything the demo needs — kuzu-in-image prod (`demo_graph`/`demo_seed` + `snapshot-demo-world.sh`), 3-card suggest with dual citations (`allowed_citation_ids`), Lane B restored (real DocumentChunks in contrast), frozen demo clock (`demo_today()`), live `improve()` re-rank in prod, `/chat` rate limit, temporal holdout backtest, RAG contrast panel, studio Today/Board/Library tabs, chat dock. Multi-user Postgres path remains in the codebase as designed-not-deployed.

**Demo (now):** https://sprout.asad.codes/studio — full Cognee story (graph join, contrast, backtest, improve) live in prod; identical locally.

**Known thin spots (don't demo these):** vision board `payload` not persisted on `Draft`; genre reveal confirm is UI-only; `api.py` `_AGENT_TOOLS` extended set not wired to `/chat` (uses `agent.py`); PulseStrip hidden in studio UI; `/gaps` returns few gaps (aggressive niche filter — honest, just thin); sign-in flow hidden (Firebase custom-domain auth never configured).

**Never cut:** the join, feedback, forget, demo path, backtest reveal.

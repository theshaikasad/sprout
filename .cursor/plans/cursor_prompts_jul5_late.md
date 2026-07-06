# Cursor prompts — Jul 5 late pass

Paste each section as its own Cursor session/prompt, in this order. Read `CLAUDE.md`
and `IMPROVEMENTS.md` first in every session — they're the source of truth for
architecture (multi-user Postgres + per-user Cognee datasets) and terminology.

**Do Prompt 0 first, before anything else below** — it's demo-day safety and
narrative honesty, not feature work, and it's urgent in a way the epics aren't.

---

## Prompt 0 — Demo narrative safety + one trajectory sentence (do this first)

```
Before any of the epic/feature work below, do these demo-safety fixes for Sprout.
These are about not showing a judge something degraded or overclaimed, plus one
small additive win — read CLAUDE.md and IMPROVEMENTS.md first for context.

1. CUT the discourse radar (Pulse) from the visible demo flow. It's Hacker-News-
   only right now, and for a slow-living/self-improvement niche the results are
   topically dead — showing it is worse than not showing it. Remove or feature-
   flag off PulseStrip from frontend/app/studio/page.tsx's default "Today" view
   for the demo. Don't delete the underlying code/route — just don't surface it
   in the pitch flow.

2. PROTECT against a judge's live OAuth sign-in landing on hollow pacing
   patterns. Real transcript coverage is only 22/128 videos right now — the
   "deepest signal" story (retention-beat pacing patterns from analyzer.py) is
   hollow on the real ingestion path until more transcripts are fetched. The
   synthetic demo world (the Lana Blakely fixture, analytics_fixture.py) already
   plants and recovers this signal correctly, so THAT path is fine and should
   stay the centerpiece. Concretely: confirm the demo script/UI steers to the
   fixed synthetic world for any "deepest signal"/pacing claim, not a live judge-
   channel connect. If a live connect flow is reachable at all during the demo,
   make sure a 0-transcript state shows an honest degrade message ("still
   learning your pacing — needs more of your videos") rather than an empty
   section that looks broken or silently wrong.

3. CORRECT any writeup/pitch materials (BUILD.md, DEMO_SCRIPT.md, submission
   text, anything judge-facing) that claim "working Sign in with YouTube"
   unqualified. OAuth is code-complete (real token exchange + real channel
   confirm via oauth.py / Firebase), but the Google consent screen's test-user
   list may not be fully populated and the flow hasn't been verified end-to-end
   with a real non-owner account. Find and fix every instance of this overclaim.
   Precise framing to use everywhere: "OAuth: code-complete, test-user config
   pending" — never "working" unqualified. This honesty is the whole brand; a
   judge who actually tries it will find the gap regardless, so get ahead of it.

4. ADD the one worthwhile additive feature for the time available: a trajectory
   sentence, "fingerprint now vs. six months ago." This is pure pandas — NOT a
   graph change. fingerprint.py already computes a recency-weighted topic/format
   distribution for "now." Add a second computation of the same distribution as
   of ~6 months ago (only videos published before that reference date, or the
   same recency-weighting re-centered on that earlier date), diff the two, find
   the topic/format with the largest weight gain, and phrase it as one sentence
   — e.g. "You've drifted from vlogs toward personal essays over the last 6
   months — exactly the shift that converts for you." Surface this prominently:
   the genre-reveal moment and/or the dashboard header, not buried in a details
   panel. This is the single best answer to "is the memory compounding, not just
   getting wider" in front of judges, for near-zero engineering cost.

5. VERIFY (don't assume) before doing anything else that the multi-user
   Postgres/per-uid refactor didn't break the three centerpiece demo flows —
   re-run each against the demo user (uid=demo) and confirm:
   - The temporal-holdout backtest still correctly names the real held-out
     videos (the hearing-loss update + the "why I'm still single" short).
   - The RAG-vs-graph contrast panel still shows both sides plus the anti-join
     Cypher query text.
   - One live one-tap-feedback round-trip: a thumbs-up/down still visibly
     re-ranks the next /suggest call for that uid. (This broke once already
     via a stale, non-uid-scoped cache — confirm the Postgres/per-uid
     migration didn't reintroduce a caching bug, now scoped per uid instead of
     global.)
   If the refactor broke any of these three, fixing them takes priority over
   item 4 above — protect what's already proven working before adding anything
   new.

Report back concretely: what you cut/hid, what you found when checking the OAuth
claims in the docs, the actual trajectory sentence generated for the demo user,
and pass/fail on each of the three protected flows.
```

---

## Prompt 1 — Frontend UX pass (quick, mechanical, do first)

```
Make these frontend changes to Sprout (Next.js, frontend/). Read IMPROVEMENTS.md
first for the current multi-user architecture (Postgres app state, per-user Cognee
datasets, uid-scoped everything).

1. DELETE Thumb Lab entirely: frontend/components/ThumbLab.tsx, its tab in
   app/studio/page.tsx, its nav entry, and the /thumbnail-review route usage on the
   frontend (leave the backend route — just stop calling it from here unless another
   feature needs it; check first).

2. ConceptCard.tsx: replace the current save/plant action buttons with a single
   star-symbol button (Gemini-style ✨) labeled "Create". Tapping it is what plants
   the idea (calls the existing plant flow) — one tap, no separate save/plant/tweak
   button row. Keep the one-tap "nailed it / not me" feedback buttons separate from
   this — those are a different action (feedback on an unselected suggestion) from
   committing to make it (Create).

3. Redesign the vision-board terminology and "Plants" section:
   - Seeds = captured ideas, unconfirmed (unchanged).
   - Planting = user confirms an idea (unchanged mechanism, "Create" button above
     triggers it).
   - "Plants" section = the creator's FULL video library — every video they've ever
     posted (from their real channel history, i.e. all of corpus["live"] +
     corpus["holdout"] equivalent for their uid), not just AI-suggested ideas that
     got posted. When a planted idea gets posted, it becomes a new plant that joins
     this same list — sprouting is the animation/moment of a new plant appearing
     among the others, not a separate section from your real history.
   - Update Garden types/API calls accordingly (check lib/api.ts's Garden type and
     backend/memory_shield/api.py's /garden route — the "sprouted" list currently
     only contains AI-tracked posted ideas; the new "plants" list needs to be the
     union of that with the full video library, deduplicated by video_id).

4. Dashboard ("Today" tab) declutter: reduce to top insights only — the single
   most important thing the creator should see today (e.g. one performance
   headline, the top 1-2 ready-to-film cards, anything urgent). Move everything
   else (full trend strip, full outlier strip, full pitch box) to secondary
   tabs/sections reachable by a click, not all visible by default on load.

5. Graph panel (GraphPanel.tsx): 
   - Make visibility a persistent user toggle (localStorage or a preference),
     not just a session-open/closed state — "hidden or visible any time" per spec.
   - CRITICAL: any chat message that fires a tool call touching the graph
     (recall_suggestions, check_competitors, scan_trends, confirm_pattern,
     search_discourse — check agent.py's TOOLS list for the full set) must show a
     live "querying your memory graph…" indicator inline in the chat WHILE the
     call is in flight, not just after ("queried while drawer closed → quiet
     invitation to open it" already exists for suggest/pitch flows in
     studio/page.tsx — extend that exact pattern to fire for every graph-touching
     chat tool call too, not just suggestion generation). If the graph panel is
     open when a query fires, auto-highlight/pulse the traced nodes live.

Test each change by running the app against the demo user (uid=demo per
IMPROVEMENTS.md) before considering this done.
```

---

## Prompt 2 — Cold-start onboarding for new creators ("for everyone, not just old creators")

```
Sprout currently assumes every creator has an established back-catalog (~60-80
videos) for genre-fingerprinting and pattern detection (PATTERN_MIN_SUPPORT=3 in
config.py). A brand-new creator with 0-10 videos gets empty or meaningless
patterns and a broken onboarding experience. Fix this — read
backend/memory_shield/{fingerprint.py, analyzer.py, agent.py} and
frontend/app/signup/page.tsx first.

1. Detect cold-start at connect time: after ingesting a new user's channel, check
   their real video count. Define tiers (adjust thresholds after checking
   PATTERN_MIN_SUPPORT/PATTERN_EARLY_SIGNAL in config.py for consistency):
   - 0 videos: pure cold start — no genre fingerprint possible at all.
   - 1-9 videos: too few for pattern-level confidence (n<3 minimum).
   - 10+: existing pipeline applies unchanged.

2. For 0-9 video creators, the genre reveal and suggestion pipeline must degrade
   gracefully, not silently produce garbage:
   - Skip pattern-confidence-gated suggestions (nothing requiring n>=3).
   - Lean on the trend radar + demand/gap-finder (scan_trends, gap_finder in
     recall.py) which don't require the creator's own history — suggest based on
     what's trending in a niche the creator self-declares at onboarding (add a
     lightweight "what's this channel about" prompt for 0-video creators, since
     there's no fingerprint to derive it from).
   - Genre reveal copy must be honest about this: not "your last 40 videos are
     really X" (false for a new creator) but something like "we don't have enough
     of your videos yet to find your patterns — here's what's converting in your
     niche right now to get started, and this gets sharper as you post."
   - As the creator posts more (crossing the 3/10 thresholds), transition them
     into the normal pattern-based flow automatically — no manual re-onboarding.

3. Update the onboarding UI (signup/page.tsx) to handle this path distinctly —
   don't show a genre-fingerprint reveal screen that has nothing real to show.

Test with a synthetic low-video-count user (mock a channel with 3 videos and one
with 0) to confirm neither path crashes or shows fabricated-sounding patterns.
```

---

## Prompt 3 — Telegram: verify and complete the real per-user connection

```
Telegram per-user linking already has real code (link_telegram(), HMAC link tokens
via TELEGRAM_LINK_SECRET, poll_forever background task — see telegram_bot.py,
api.py). The user-facing report is that the Telegram connection isn't actually
working end-to-end. Don't assume it's broken OR that it's fine — verify the full
real flow and fix whatever's actually wrong:

1. Trace the complete flow: does the frontend have a UI step where a signed-in
   user gets a link code/deep-link to message the bot with? If missing, build it
   (a "Connect Telegram" button in settings/onboarding that calls a backend route
   generating their HMAC link token, shown as a `/start <token>` deep link or a
   code to paste into the bot).
   
2. Test for real: create a test user, generate their link token, message the bot
   with it via the actual Telegram API (not a mock), confirm link_telegram() gets
   called with the RIGHT uid, confirm users.telegram_chat_id is set correctly in
   Postgres.

3. Test a real send: trigger a proactive nudge for that specific test user and
   confirm it arrives at the right chat_id, not the global TELEGRAM_CHAT_ID env var
   (check telegram_bot.py — if send calls still default to a single global
   TELEGRAM_CHAT_ID anywhere instead of looking up the per-user chat_id from
   Postgres, that's the bug).

4. Test the reply path: message the bot as that test user, confirm poll_forever
   correctly attributes the incoming message to their uid (not the demo user or
   nobody), and that it saves as a seed under THEIR account.

Report exactly what was broken and what you fixed — don't just say "confirmed
working" without describing the actual failure mode you found, if any.
```

---

## Prompt 4 — Production kit (closes the "vidIQ ceiling" complaint)

```
Real creator feedback: "Sprout tells me what to make, what hook, what title,
what packaging — then I close the app and go do the two hardest parts alone:
writing the thing and making the real thumbnail. The concept-art is Ghibli
mood-art, not a shippable asset." Close one real step of that gap. This is
"Epic 5: Production kit" in IMPROVEMENTS.md.

Build TWO new generated artifacts per planted idea, both derived from data
already computed (no new data sources needed — this is a synthesis problem):

1. **A real thumbnail brief** (not an image — a structured, designer-executable
   spec): exact overlay text (the actual words to use, not a vibe), composition
   layout (subject placement, expression, contrast direction), and an explicit
   citation to 1-2 of the creator's own highest-CTR past thumbnails as visual
   precedent (pull from thumbs.py's vision-analyzed packaging attributes —
   check what's already extracted per video and reuse it, don't re-analyze).
   Output as structured text/JSON a human designer (or the creator in Canva)
   could execute directly, alongside the existing Ghibli concept-art (keep both —
   concept art stays as the emotional/vision-board artifact, this is the new
   production artifact).

2. **A script skeleton keyed to retention beats**: a literal beat-by-beat outline
   with target durations, derived from analyzer.py's pacing PatternNodes (the
   "intros >40s bleed, demos hold" signal) and beats.py's beat-type taxonomy,
   applied to the card's chosen format/hook. E.g. "Hook (0:00-0:08): cold-open
   question — your data shows intros over 40s cost ~20% retention, so skip
   preamble. Context (0:08-0:25): ... Demo (0:25-...): this is where your
   retention historically holds — spend real time here." Every duration/claim in
   this skeleton must trace to a computed pattern, same anti-slop rule as
   everywhere else in this codebase (no LLM-invented numbers).

3. Surface both in the UI on a planted idea's detail view — a new "Production
   kit" section/tab alongside the existing concept art, not replacing it.

4. Add backend generation functions (likely in a new module, e.g.
   production_kit.py) called at planting time or on-demand, cached same as
   concept art. Add API routes + wire into the frontend idea detail view.

Read CLAUDE.md's "Pattern learning & the honest why" section for the exact
citation/confidence-tiering rules this must follow — every claim in the brief and
skeleton needs a receipt, same standard as concept cards.
```

---

## Prompt 5 — Competitor alerts: pull, not push (closes the anxiety-machine complaint)

```
Real creator feedback: proactive Telegram alerts about competitors overperforming
are structurally the same "someone else is winning" ping the calm Ghibli aesthetic
is supposed to protect against — the anxiety-machine and the anti-anxiety-machine
are currently the same feature. This is "Epic 6: Competitor calm" in
IMPROVEMENTS.md (paired with the Telegram work in Prompt 3 — do that first).

1. Find every place a competitor-overperforming signal currently triggers or could
   trigger a PUSH notification (Telegram send, or any proactive nudge path in
   refresh.py / the scheduled refresh loop / nudges logic). Remove or gate all of
   them — competitor-watch data should be pull-only by default: visible when the
   creator opens check_competitors in chat, or as a quiet card in the dashboard's
   "top insights" (only when they choose to look), never pushed to their phone.

2. If you keep ANY proactive competitor nudge at all, gate it behind a much
   higher bar than "outperforming" — specifically: only fire if a competitor's
   overperforming video is topically adjacent to an idea the creator ALREADY has
   seeded or planted (i.e., it's actionable to something they're already
   thinking about, not generic comparison anxiety). Add a preference toggle
   (preferences.competitor_alerts per IMPROVEMENTS.md's planned schema addition)
   defaulting to OFF, not on — opt-in, not opt-out.

3. Audit all existing proactive nudge copy (idea-completion, celebration,
   consistency reminders per CLAUDE.md's "three kinds" of reminders) — confirm
   none of them reference competitor comparison; if any do, rewrite to be about
   the creator's own trajectory only.

Report which specific push paths you found and removed/gated — be concrete, this
is a policy bug as much as a code bug and I want to know exactly what was firing.
```

---

## Prompt 6 — Episodic memory + self-audit (the highest-value fix — do this even if time is short)

```
Real creator feedback (their words, verbatim, this is the target experience):
"it told me to cold-open my demos, I did, my retention at 0:40 went up 12%, and
now it's stopped suggesting the long intros." Right now the entire feedback loop
from suggestion to outcome is a silent feedback_weight bump nobody sees
(lifecycle.py's mark_sprouted). This is "Epic 1 (episodic memory) + Epic 2
(self-audit recall)" in IMPROVEMENTS.md, named there as the source of truth for
the "Memory Shield effect" thesis — build it for real, this is the single
highest-value thing in this whole batch of work.

1. **New Postgres table `suggestion_episodes`** (add to db/models.py per
   IMPROVEMENTS.md's Phase 0 plan): records the full chain per suggestion —
   episode_id, uid, the suggested card's trace (topics/formats/hooks/patterns
   cited — reuse the existing Trace shape from recall.py), which specific claim
   was made (e.g. "cold-open hook predicted +15% early retention"), the decision
   (did the creator plant this idea, and later sprout/post it, and did the
   posted video's actual hook/format match what was suggested or did they
   deviate — record both), and once posted: the outcome (the specific promised
   metric's actual before/after — e.g. retention at the specific timestamp the
   pattern referenced, not just overall retention).

2. **Wire episode creation** at suggestion time (recall.py's suggest() — every
   card returned should create or reference an episode), at decision time
   (lifecycle.py's plant_idea/mark_sprouted — link the draft to its episode,
   record whether the posted video actually matches the suggested hook/format),
   and add a **Cognee mirror**: SuggestionEpisodeNode + an `episodes` node_set per
   IMPROVEMENTS.md's plan, so this is queryable from the graph too, not just SQL.

3. **Build the actual outcome computation** (`advice_track_record()` per
   IMPROVEMENTS.md — this is the real math, must live in Python/pandas, never
   LLM-invented, same rule as everywhere else): once a sprouted video has enough
   analytics data, check whether the SPECIFIC promised effect materialized — if
   the episode's claim was "cold-open → better early retention," pull that
   video's actual retention curve at the relevant timestamp and compare to the
   creator's baseline. Compute a real before/after, not a vibe.

4. **Surface it as a real, narrated moment** — not a silent weight bump. When an
   episode resolves (positive or negative), this should generate an actual
   visible event: a chat message and/or Telegram nudge in the creator's own
   voice-of-data: "You cold-opened this one like we discussed — retention at
   0:40 went from X% to Y% (up 12%) vs your baseline. That pattern just got
   stronger." AND the honest negative case: "You tried the cold-open hook, but
   retention didn't move this time — I'm not going to lean on that pattern as
   hard next time." Both cases are real, both use computed numbers, both close
   the loop the creator can actually see.

5. **Add a "track record" view** — advice_track_record() should also power a
   UI surface (dashboard or a dedicated view) showing the creator's own history
   of "here's what we suggested, here's what you did, here's what happened" —
   this is the self-audit recall piece, and it's the artifact that makes
   "memory that knows you" viscerally real instead of an abstract claim.

This touches recall.py, lifecycle.py, a new episodes.py or similar module,
graph_models.py (new DataPoint), db/models.py (new table), and needs new API
routes + frontend surfaces (a chat-message type for episode resolution, a
track-record view). Take the time to get the computation genuinely correct —
this is the feature a creator would actually tell their friends about, per their
own words; a fake or approximate version of this would be worse than not having
it, since the whole pitch is that these numbers are always real and computed.
```

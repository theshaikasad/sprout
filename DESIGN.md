# Sprout — what it is and how it actually works

*The human-readable explainer. `CLAUDE.md` stays the terse build spec; this file tells the whole story in order, including the mechanics we kept referring to in shorthand (one-tap teaching, CTR patterns, the genre fingerprint, and why Cognee instead of a markdown file).*

---

## 1. The product in one paragraph

Sprout is a quiet creator companion with a **memory of you**. You sign in with YouTube once; it reads your real analytics, tells you your own genre, and builds one persistent memory of what *you* make and what *converts for you*. From then on it does the research you'd otherwise doomscroll for — trends in your true niche, your real competitors, what your audience actually responds to — and brings it to you as calm, cited, falsifiable suggestions you react to with one tap. Every reaction makes the memory sharper. Every idea you mention is quietly caught, grown on a vision-board (seed → planted → sprouted), and celebrated when you post it. The promise: **create more, consume less** — and never open YouTube Studio just to *check*.

---

## 2. The user's journey (the whole product, in order)

1. **Connect** — one click, "Sign in with YouTube" (OAuth). No forms, no niche dropdown, no onboarding questionnaire about your content. The system reads instead of asking.
2. **The genre reveal** — a few minutes later: *"Your last 40 videos are really three things: slow-living vlogs, self-improvement essays, and personal storytelling — and it's the personal ones, the vulnerable ones, that actually grow you. Right?"* You confirm or correct (that's the memory's first lesson). Then the garden **paints itself to match you** — the board's background becomes a warm painted scene generated from your genre.
3. **Daily life** — two surfaces, one brain:
   - **Telegram** (ambient): occasional earned messages — *"your last video is beating your median retention 🎉"*, *"a competitor's RAG video is overperforming — you wanted to make one, good time?"*, *"what are you making this week?"* You reply in one line; it's saved.
   - **The dashboard** (deliberate): the garden. What greets you is your consistency (gentle, never a guilt streak) and your ideas waiting. Numbers appear only as receipts behind suggestions.
4. **Ideas grow** — mention an idea in passing and it lands in the **seed tray** silently. When it's concrete, the agent asks *"plant it?"* — planted ideas get painted concept-art and sit on the board. When you post the video, the card **sprouts** and settles into your visible history of growth. Unplanted seeds compost after a few weeks.
5. **The memory sharpens** — every card you confirm or reject, every pattern hypothesis you validate, every video you post feeds back into the memory. Next week's suggestions are measurably more *you* than last week's.

---

## 3. Where the data comes from — yes, OAuth is the spine now

**We completely switched.** The old version used only the public Data API, which meant it could see *that* a video got views but never *why* — and "why it converted" is the entire product. So:

- **Your channel (private, via OAuth + YouTube Analytics API):** audience-retention curves, **CTR + impressions**, traffic sources (search / suggested / browse), subscribers gained *per video*, audience demographics, when your viewers are online. This is the data ChatGPT can never have and the creator never has to paste.
- **Everyone else (public Data API):** competitors' and trending videos' titles, thumbnails, views, likes, publish dates, transcripts. We get their *packaging and topics*, never their retention — and the product says so honestly instead of inventing scores.
- **OAuth practicals:** Google "Testing mode" app — up to 100 test users, no review process, 7-day tokens. Fine for a hackathon and early users.
- **The demo:** judges won't OAuth their own channel on stage, so the live demo runs the *real system* on a fixed synthetic world — a sample channel (**@LanaBlakely**, 1.65M slow-living/self-improvement vlogger; real public videos + view counts) with fabricated-but-internally-consistent private analytics. Every number the agent cites is truthful relative to that world.

### What CTR is and why we lean on it

CTR = of the people YouTube *showed* your thumbnail (impressions), the % who clicked. It's the cleanest measure of **packaging** (title + thumbnail), fully separated from content quality:

- **High CTR, low retention** → packaging wins, content pacing loses viewers. Sprout's framing: *"People are clicking — your packaging is landing, that's the hard part. They slip around 0:40; want two ways to hold them?"*
- **Low CTR, high retention** → the opposite: the video is good, the package undersells it.

CTR is private — you have it only for your own videos. That's exactly why patterns like *"your titles with a number average 2.1× CTR"* are a moat: nobody else can compute them, and tools like vidIQ literally *invent* an "estimated CTR" score instead. Ours is computed in pandas from your real rows, always shown with the sample size.

---

## 4. The memory — and the honest answer to "why not just a markdown file?"

Fair question, because the *simplest* memory really is a text file pasted into the prompt. Here's the honest breakdown of where that dies and where Cognee actually earns its keep.

**What's in the memory:** ~80 of your videos (with metrics, topics, hooks, formats, timestamped beats), the pattern-nodes computed from them, hundreds of competitor/trend videos, your drafts and seeds, and your preferences — all as **nodes with typed edges** (`Video-covers→Topic`, `Video-exhibits→Pattern`, `Idea-derived_from→Trend`…), each node carrying a **feedback weight**.

**A markdown file would honestly suffice for one slice:** your preferences (goals, tone, interruption budget, "never suggest X"). That's a paragraph. If that were the whole memory, Cognee would be overkill — we store it as nodes anyway only so it can gate the same queries.

**Where the file (and plain RAG) breaks — the three places Cognee genuinely shines:**

1. **The join.** The killer query is a *traversal*: your converting Topics → trending/competitor Videos semantically near them → their Creators → filtered to your size band → ranked against each channel's own baseline. That's a multi-hop walk across node_sets. A markdown file can't do it at all; vector search alone returns "similar text," not "videos by channels YouTube recommends next to you, on topics that convert *for you*." This join **is** the product's research quality, and it's the demo's side-by-side contrast: plain `search()` vs. the orchestrated graph query. The demand/gap finder rides the same bridge in reverse — it's a **graph anti-join** (`NOT EXISTS`: trending, near your fingerprint, but *no* path reaches a topic you already cover), a set-difference no similarity search can express either. These two — the join and the anti-join — are the two places we hand judges a raw Cypher query instead of prose.
2. **Memory that learns (weights).** Every node has a native `feedback_weight`. One-tap feedback doesn't append a note saying "user liked this" — it **numerically reweights the exact nodes** that produced the suggestion, and the next retrieval reads those weights. A file can record feedback; it can't *rank by it*. This is `improve()`/`memify()`, and it's why the memory gets **sharper, not just bigger** — Cognee's own thesis, demonstrated live.
3. **Scoped forgetting.** Trends are ingested into dated datasets (`trends_2026_w27`) and `forget()` drops whole expired datasets nightly; unplanted seeds compost after ~3 weeks; "never suggest this again" is a real deletion plus a durable exclusion node. A memory that only grows turns into noise — decay is half of "sharper."

Plus the quiet fourth: **provenance**. Because every suggestion is assembled from retrieved nodes, every claim carries its receipts (which videos, which pattern, what n). A prose file gives the LLM vibes; a graph gives it citations.

**Rule of thumb we build by:** preferences = trivially file-able; *portfolio + niche + weights + decay* = the graph. The memory isn't big — it's **structured, weighted, and churning**, and that's the shape files are worst at.

---

## 5. The analyzer — how patterns are actually learned

Nothing here is the LLM "noticing" things. Strict division of labor:

- **LLM (gpt-4o-mini, batch, cached)** turns messy inputs into *categorical labels*: each video's topics, format, hook type, and timestamped beats (intro/context/demo/sponsor/CTA/outro) from the transcript. One budgeted call per video, cached to disk forever. It never touches a number.
- **Vision model** does the same for each video's static thumbnail: face present? text overlay word count? contrast? One cached call per thumbnail.
- **Python (pandas)** does *all* the math over a local analytics table (videos × features × outcomes): group by label, compare CTR/retention/subs-gained, effect sizes, sample sizes. Where "which hook wins" is actually decided.
- **Confidence tiering (the anti-slop guardrail):** a pattern only surfaces past a support threshold. `n=2` → "early signal", `n=10` consistent → a rule. Always stated as correlation with `n`, never causation.
- **Stratified by format:** Shorts and long-form are never pooled — their physics differ.
- **The deepest signal:** transcripts are timestamped and retention curves are time-indexed, so we align *beats* onto the curve: "your demos hold attention; intros over 40s bleed 20% of viewers." Pacing patterns no keyword tool can see.
- **The human supplies causality:** the agent proposes each pattern as a *hypothesis* — "your demo-heavy videos hold attention better, right?" — and your confirm/deny is what promotes it to a rule (or buries it). Machine detects; human judges.

Results are written into the graph as **PatternNodes** with `exhibits` edges from the videos that show them. Computation runs on a schedule (new ingest, daily cron, or on demand) — never live during chat. At ~80 videos it's milliseconds, so each refresh just recomputes everything.

---

## 6. One-tap teaching — the full mechanics

This is the loop that makes the memory *yours*, so here it is end to end:

**Every suggestion is built from a known trace.** When recall assembles a concept card — say *"a hands-on eval-tooling video, cold-open question hook, ~12 min"* — it isn't freeform text. The retrieval returned specific nodes: `Topic(evals)`, `Hook(cold-open-question)`, `Format(hands-on tutorial)`, and the PatternNodes cited as receipts (*"cold-opens: +15% early retention, n=7"*). The card remembers exactly which nodes built it.

**The card carries two buttons: "nailed it" / "not me."** One tap, no typing, no explaining. Mechanically:

1. The tap becomes a `FeedbackEntry` (score +1/−1) tied to that recall's QA id — Cognee's native feedback machinery.
2. `improve()` runs, which bumps or dips **`feedback_weight` on exactly those nodes** — the hook, the format, the topic, the patterns behind *that* card. Not a global thumbs-up: a targeted nudge on the trace.
3. The next recall reads the weights (`feedback_influence`). Confirmed traces rank higher; rejected ones sink and stop surfacing.

**Why one tap matters:** a tired creator will never write feedback paragraphs, and they shouldn't have to say *why* — we already know which nodes made the card, so a bare yes/no lands on precisely the right memories. The user teaches by reacting; the system does the bookkeeping. And the effect is *visible*: reject two shorts-ideas cards and the next batch skews long-form. The demo shows this happening live.

**The same machinery drives three other flows:**
- **Pattern hypotheses** — "your intros over 40s lose people — sound right?" Confirm strengthens the PatternNode, deny buries it. (The genre reveal itself is the first such confirm.)
- **Posted videos** — when a planted idea sprouts and the video performs, its Hook+Format+Topic trace gets a positive bump automatically: reality's own one-tap.
- **Hard rejection** — "never suggest X again" isn't a reweight, it's `forget()` plus a durable exclusion preference that even nightly auto-discovery respects.

**And decay handles what feedback can't reach:** stale trend datasets are dropped nightly once past their window; unplanted seeds compost after a few weeks. Feedback adds signal, decay removes noise — the memory sharpens from both ends. That's the sentence "reweights the exact hook, format and topic behind that card; stale trends decay out on their own; unplanted seeds compost" unpacked.

---

## 7. Genre — getting it right from the videos alone

"Pick your niche" is a dropdown lie — a creator is not one label. Sprout derives the genre and *tells* the user:

1. **Label every video** (batch extraction): topics + format per video, embedded as Topic nodes.
2. **Weight by conversion, not frequency.** Each topic×format cell is scored by the **growth score** of its videos — subs-gained (primary) + retention + CTR + watch-time, components kept separate for explanation. Making many vlogs that don't convert ≠ your genre; the three tutorials that each gained 400 subs are.
3. **Recency-weight** so the fingerprint follows channel drift, and require minimum support per topic so one lucky video doesn't define you.
4. **The output is a weighted distribution** — e.g. *"LLM tutorials 34% (and 1.8× conversion), career-in-AI 22%, math explainers 18%"* — not a category. This fingerprint is the product's spine: it phrases the onboarding reveal, filters which trends are worth surfacing, anchors competitor triangulation, and paints the board background.
5. **It's confirmed, not asserted.** The reveal ends with "— right?" and the user's answer is the fingerprint's first reweight. If we got it wrong, the memory learns that *immediately*.

**Competitors fall out of the same fingerprint:** triangulate (a) channels YouTube's *suggested-video traffic* actually recommends next to you — the gold signal from Analytics, (b) fingerprint-neighbors by embedding, (c) who ranks on your converting topics — then filter to a **0.3×–10× subscriber band** (comparing you to MrBeast is useless *and* demoralizing). Their videos are surfaced by **outlier score** (views ÷ that channel's own median) and velocity, never raw views — "big channel is big" is not a signal.

---

## 8. The chat agent — react, don't compose

- **Context pack every turn:** preferences + relevant graph recall + board & seed tray + the cron's "since we last talked" digest. Openers carry earned news with zero live work.
- **Reads** (`get_my_performance`, `scan_trends`, `check_competitors`, `search_discourse`, `get_drafts`, `optimize_title_desc`, `validate_packaging`) fire when a reply needs a fact — hard rule: **the agent may not state a number that didn't come out of a tool.** Reads hit last night's caches; live scans only on explicit "check now."
- **Writes** (`save_idea`, `mark_done`, `add/remove_competitor`, `set_preference`, `confirm/reject_pattern`, `snooze_nudges`…) fire only on explicit command or a confirmed proposal; destructive ones always confirm. "Remove @X as a competitor" both removes the node *and* writes a durable exclusion.
- **Seed capture is the agent's job, not a parser's:** ideas converge over multiple messages, so a silent end-of-turn pass distills them into cards (title, angle, format, provenance) — never raw chat logs in the graph — and embedding-matches against existing seeds/drafts to update instead of duplicate.
- **Model split:** the user-facing chat runs on a frontier model via API; all batch extraction stays on gpt-4o-mini. We don't compete with ChatGPT — **we arm it** with your private numbers, a weighted memory, proactivity, and tools. *"ChatGPT is a brilliant stranger every session; Sprout is the same brain that's known you for months."*

---

## 9. System design

```
                        ┌─ REAL PATH: OAuth + YT Analytics API
  SOURCES ──────────────┤
  (YouTube Data API,    └─ DEMO PATH: world.py synthetic fixture
   transcripts, HN/Reddit)          │
        │                           │
        ▼                           ▼
  .cache/  ← raw JSON, transcripts, extractions, thumbs, art (disk, forever)
        │
        ▼
  ANALYTICS TABLE (pandas, .cache/analytics.parquet)   ← ALL math lives here
        │
        ▼
  ANALYZER (analyzer.py) → patterns.json (statement, n, effect, tier, stratum)
        │
        ▼
  COGNEE GRAPH (.cognee/) ← Lane A skeleton+patterns · Lane B cognify(transcripts)
  node_sets: my_channel / competitors / trends / drafts (+ holdout excluded)
        │
        ▼
  AGENT (frontier model + tool registry, context pack per turn)
        │
        ▼
  SURFACES: FastAPI :8000 → Next.js garden :3000  ·  Telegram bot
                  ▲
  SCHEDULER (in-process) — daily analytics · nightly trends+forget · compost · nudges
```

**Four stores, strict roles:** `.cache/` (raw API responses, transcripts, extractions, images — never re-pay a call) · `analytics.parquet` (the stats table — math is tabular, don't force it through a graph) · `.cognee/` (the memory: nodes, edges, weights — retrieval, join, citation) · `ideas.json` (operational board state, mirrored into the `drafts` node_set).

**One process rule:** kuzu is single-writer, so API + agent + scheduler + Telegram bot share **one** uvicorn process and one asyncio write-lock. The ingest CLI is the only other writer and runs with the server stopped.

**The demo world is self-validating:** `world.py` *plants* the ground-truth patterns into the synthetic analytics (number-titles get ~2× CTR; >40s intros get a retention cliff at 0:40; demo beats plateau; subs ∝ views × retention × topic affinity; all consistent with the real public view counts) — and the analyzer must *recover* them. Every demo claim is then truthful relative to the world, and the pipeline proves itself.

**Build order** (dependency spine in bold): env sanity → **world fixture** → features (beats/is_short/packaging) → **analyzer + table** → **ingest v2** (PatternNodes, exhibits, node_sets, holdout) → fingerprint + competitors → **recall v2, the killer query + the anti-join gap-finder** (the tuning step) → feedback + forget → agent + board lifecycle → API + garden frontend → polish (concept art → board background → Telegram → OAuth real path → cron timers). Never cut: the join, feedback, forget. Considered-and-cut for this build (real ideas, deliberately out of scope): a 4-hop idea-citation chain, cross-competitor pattern corroboration, a temporal pattern-decay check.

**Demo centerpiece:** temporal-holdout backtest — the graph is blind to everything after **2026-04-01**, recommends from her pre-cutoff patterns (personal/vulnerable essays convert 3–9.5×), then we reveal she actually made both predicted videos in the held-out months — "Losing my hearing: 2 years later" and "When people ask why I'm still single…" — and they were her best performers of those months. Plus the side-by-side plain-RAG vs. graph-join contrast, and one live one-tap feedback beat that visibly reorders the next suggestion. (All baselines trailing/recency-weighted — her channel peaked in 2024, and a decline story must never surface.)

---

## 10. What we deliberately don't do

No raw video/frame analysis or ASR (transcripts + one cached thumbnail call per video). No invented scores (vidIQ's "estimated CTR" is the imitate-clickbait trap with a decimal point). No fine-tuned model (a real training set would need `{title → CTR}` at scale; CTR is private, so that data doesn't exist yet — roadmap once the flywheel earns it). No causal claims, only correlations with `n` and the user's own confirmation. No guilt: every metric is reframed as encouragement plus a next action, and silence within the interruption budget is a feature.

# Sprout — 60-second demo walkthrough

Live: **https://sprout.asad.codes/studio** (no sign-in needed).
Local: `uvicorn memory_shield.api:app --port 8000` from `backend/`, `npm run dev` from `frontend/`.

**What it is, one line:** an AI companion with a persistent, improving memory of one YouTube
creator — every suggestion is retrieved from a knowledge graph of her real videos + analytics and
must cite receipts, or it's discarded.

## The 60 seconds

1. **Framing (10s)** — the top strip says it all: live demo wearing **@LanaBlakely**'s channel
   (1.65M subs). ~60 real videos, transcripts, and analytics distilled into the knowledge graph on
   the right (~540 nodes). *"Nothing here is mocked."*
2. **Cited cards (15s)** — three concept cards auto-load. Point at the receipts strip under each:
   *"her video that proves the pattern, plus one proving demand — uncited ideas get discarded."*
   Click a card → the exact retrieval path lights up in the graph (trend → topic → her videos →
   format/hook).
3. **Teach it (10s)** — hit *"you're wrong"* on a card → it regenerates and the batch visibly
   shifts. That's `improve()` reweighting the graph live, not a UI trick.
4. **The backtest (15s)** — "Why believe it" → **break the seal**. The memory was blinded to her
   last 3 months, suggested a direction, and named the videos she actually went on to make —
   champion *"Losing my hearing: 2 years later"* at **2.06×** her median.
5. **Not just RAG (10s)** — **see the contrast**: the same question to plain vector search
   (fluent, uncited prose) vs the graph join (cited concepts), side by side.

## If they want depth

- **Chat** ("ask sprout"): a tool-gated agent over the same memory — it may only state numbers
  that came out of a tool call.
- **Library tab**: the raw corpus — her channel, six size-band competitors, trend videos.
- **Board tab**: ✨ Create on a card → a shoot brief lands on the vision board with a target date
  from her real posting rhythm.
- **Stack, one breath:** FastAPI + Cognee (Kuzu graph + LanceDB vectors) + a pandas pattern layer
  + gpt-4o-mini; Next.js 16 + Tailwind; Cloud Run deployed by GitHub Actions (WIF, Secret
  Manager), with the frozen demo world baked into the Docker image.

## Honest answers to expected questions

- **"Is the data real?"** Her videos, transcripts, and view counts are real (YouTube Data API).
  Retention/CTR are synthesized to be consistent with her public numbers — YouTube only shares
  those with the channel owner. Multi-user OAuth ingestion is implemented in the codebase but not
  wired to the public demo.
- **"Why is the demo frozen in time?"** The demo world's clock is anchored to the corpus snapshot
  (`demo_today()`) so the fixture never reads as an abandoned channel.

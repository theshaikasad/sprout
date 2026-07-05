"use client";

/* eslint-disable @next/next/no-img-element */

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  api,
  type BacktestResponse,
  type Cadence,
  type GraphData,
  type Garden,
  type Idea,
  type Library,
  type Pulse,
  type SuggestResponse,
  type Trace,
  type Track,
  type Trend,
} from "@/lib/api";
import { watchAuth, type User } from "@/lib/firebase";
import ConceptCard from "@/components/ConceptCard";
import DashboardBackdrop from "@/components/DashboardBackdrop";
import SproutDashboard from "@/components/SproutDashboard";
import GraphPanel from "@/components/GraphPanel";
import ChatDock from "@/components/ChatDock";
import BacktestReveal from "@/components/BacktestReveal";
import RagContrast from "@/components/RagContrast";
import ChannelShelf from "@/components/ChannelShelf";
import PitchBox from "@/components/PitchBox";
import IdeasBoard from "@/components/IdeasBoard";
import OutlierStrip from "@/components/OutlierStrip";
import CoachMarks from "@/components/CoachMarks";
import ConnectTelegram from "@/components/ConnectTelegram";
import Thumb, { fmtViews } from "@/components/Thumb";
import { touchesGraph } from "@/lib/graphTools";
import { Logo } from "@/components/Logo";

const GRAPH_OPEN_KEY = "sprout-graph-open";

const THINKING = [
  "bridging trend → your topics (vector hop)…",
  "walking covers / uses / has_format edges…",
  "checking what actually converted…",
  "drafting concepts against the evidence…",
];

type Tab = "today" | "board" | "library";

const TABS: { id: Tab; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "board", label: "Board" },
  { id: "library", label: "Library" },
];

const UPLOAD_STATUS = {
  above: { label: "converting", cls: "text-accent" },
  on_track: { label: "on pace", cls: "text-dim" },
  under: { label: "slow", cls: "text-amber" },
} as const;

function Studio() {
  const search = useSearchParams();
  const [tab, setTab] = useState<Tab>("today");
  const [trends, setTrends] = useState<Trend[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [suggestion, setSuggestion] = useState<SuggestResponse | null>(null);
  const [activeTrend, setActiveTrend] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [thinkStep, setThinkStep] = useState(0);
  const [selectedCard, setSelectedCard] = useState<number | null>(null);
  const [pitchTrace, setPitchTrace] = useState<Trace | null>(null);
  const [pitchSeed, setPitchSeed] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [backtestBusy, setBacktestBusy] = useState(false);
  const [contrastOpen, setContrastOpen] = useState(false);
  const [offline, setOffline] = useState(false);
  const [garden, setGarden] = useState<Garden | null>(null);
  const [lib, setLib] = useState<Library | null>(null);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [cadence, setCadence] = useState<Cadence | null>(null);
  const [track, setTrack] = useState<Track | null>(null);
  const [pulse, setPulse] = useState<Pulse | null>(null);
  const [savedTitles, setSavedTitles] = useState<Set<string>>(new Set());
  const [chatOpen, setChatOpen] = useState(false);
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphQuerying, setGraphQuerying] = useState(false);
  const [chatGraphPending, setChatGraphPending] = useState(false);
  const [showAllConcepts, setShowAllConcepts] = useState(false);
  const [me, setMe] = useState<User | null>(null);
  const [memorySharpened, setMemorySharpened] = useState(false);
  const improveToasted = useRef(false);
  const prevSuggest = useRef<SuggestResponse | null>(null);

  // the graph shows whichever retrieval happened last: a card's or a pitch's
  const trace: Trace | null =
    pitchTrace ??
    (suggestion && selectedCard !== null
      ? (suggestion.cards[selectedCard]?.trace ?? null)
      : null);

  const refreshIdeas = useCallback(() => {
    api
      .ideas()
      .then((list) => {
        setIdeas(list);
        setSavedTitles(new Set(list.map((i) => i.title)));
      })
      .catch(() => {});
  }, []);

  const runSuggest = useCallback(async (trend?: string) => {
    setLoading(true);
    setGraphQuerying(true);
    setSelectedCard(null);
    setPitchTrace(null);
    try {
      const s = await api.suggest(trend);
      if (prevSuggest.current && track?.improved_labels?.length) {
        setMemorySharpened(true);
      }
      prevSuggest.current = s;
      setSuggestion(s);
      setActiveTrend(s.trend);
      setSelectedCard(0);
    } catch {
      setOffline(true);
    } finally {
      setLoading(false);
      setGraphQuerying(false);
    }
  }, [track?.improved_labels]);

  const runBacktest = useCallback(async () => {
    setBacktestBusy(true);
    try {
      setBacktest(await api.backtest());
    } finally {
      setBacktestBusy(false);
    }
  }, []);

  useEffect(() => {
    api.trends().then(setTrends).catch(() => setOffline(true));
    api.graph().then(setGraph).catch(() => setOffline(true));
    api.library().then(setLib).catch(() => {});
    api.cadence().then(setCadence).catch(() => {});
    api
      .track()
      .then((t) => {
        setTrack(t);
        if (t.improved_labels?.length && !improveToasted.current) {
          improveToasted.current = true;
          flash(
            `Memory sharpened: ${t.improved_labels.slice(0, 3).join(", ")} ↑ from your uploads`,
          );
        } else if (t.improved_nodes > 0 && !improveToasted.current) {
          improveToasted.current = true;
          flash(
            `improve(): ${t.improved_nodes} memory nodes reweighted — no report needed`,
          );
        }
      })
      .catch(() => {});
    api.pulse().then(setPulse).catch(() => {});
    refreshIdeas();
    api.garden().then(setGarden).catch(() => {});
    runSuggest("slow living");
    if (search.get("proof") === "1") runBacktest(); // onboarding: earn trust first
    return watchAuth(setMe);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runSuggest, refreshIdeas, runBacktest]);

  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setThinkStep((s) => (s + 1) % THINKING.length), 1400);
    return () => clearInterval(t);
  }, [loading]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(GRAPH_OPEN_KEY);
      if (stored === "true") setGraphOpen(true);
    } catch {
      /* private browsing */
    }
  }, []);

  function toggleGraph(open?: boolean) {
    setGraphOpen((prev) => {
      const next = open ?? !prev;
      try {
        localStorage.setItem(GRAPH_OPEN_KEY, String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
    if (open === true || open === undefined) {
      setChatGraphPending(false);
    }
  }

  async function handlePlantSeed(id: string) {
    try {
      await api.plantIdea(id);
      flash("🌱 planted — it takes root on your board");
      api.garden().then(setGarden).catch(() => {});
      refreshIdeas();
    } catch {
      flash("couldn't plant — try again");
    }
  }

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  async function decay(trend: string) {
    const res = await api.decay(trend);
    flash(`forget(): "${trend}" decayed — ${res.deleted_nodes} nodes removed`);
    api.trends().then(setTrends).catch(() => {});
    api.graph().then(setGraph).catch(() => {});
    if (activeTrend === trend) runSuggest();
  }

  // planned publish date from the channel's real rhythm
  function defaultTarget(): string | undefined {
    if (!cadence?.last_published || !cadence.median_gap_days) return undefined;
    const next = new Date(cadence.last_published);
    next.setDate(next.getDate() + cadence.median_gap_days);
    const base =
      next.getTime() > Date.now() ? next : new Date(Date.now() + 2 * 86400000);
    return base.toISOString().slice(0, 10);
  }

  const firstName = lib?.creator.title.split(" ")[0] ?? "creator";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const avatar = me?.photoURL || lib?.creator.avatar || "";

  const underCount = track?.uploads.filter((u) => u.status === "under").length ?? 0;
  const trackedCount = track?.uploads.length ?? 0;
  const watchHeadline =
    trackedCount === 0
      ? null
      : underCount === 0
        ? "All quiet — your uploads are doing what they usually do."
        : underCount < trackedCount
          ? `${trackedCount - underCount} of your last ${trackedCount} uploads are fine — ${underCount} running slow.`
          : "Your recent uploads are under your usual pace — today's concepts are the response.";

  const today = new Date().toISOString().slice(0, 10);
  const overdueIdeas = ideas.filter(
    (i) =>
      i.target &&
      i.target.slice(0, 10) < today &&
      i.status !== "posted",
  );
  const todayHeadline =
    garden?.consistency?.encouragement ||
    watchHeadline ||
    "Your garden is waiting — here's what matters today.";

  const conceptCards = suggestion?.cards ?? [];
  const visibleCards = showAllConcepts ? conceptCards : conceptCards.slice(0, 2);

  return (
    <>
      <DashboardBackdrop />
      <main className="relative z-10 mx-auto max-w-6xl px-6 pb-24">
      {/* top bar — brand · rooms · you */}
      <header className="flex flex-wrap items-center justify-between gap-3 py-4">
        <Link href="/">
          <Logo />
        </Link>

        <nav className="flex rounded-xl border border-line bg-raised p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-4 py-1.5 text-sm transition-colors ${
                tab === t.id ? "bg-raised-2 font-medium text-fg" : "text-dim hover:text-fg"
              }`}
            >
              {t.label}
              {t.id === "board" && ideas.length > 0 && (
                <span className="ml-1.5 font-mono text-[10px] text-accent">{ideas.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => toggleGraph()}
            title="Show the memory graph"
            className={`btn-ghost px-3.5 py-2 text-xs font-medium ${
              graphOpen ? "border-accent/60 text-accent" : ""
            }`}
          >
            ⛁ Memory
          </button>
          <Link href="/signup" title={me ? `${me.displayName} — switch channel` : "switch channel"}>
            {avatar ? (
              <img
                src={avatar}
                alt=""
                referrerPolicy="no-referrer"
                className="h-8 w-8 rounded-full border border-line transition-transform hover:scale-105"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-raised font-semibold text-dim">
                {firstName[0]}
              </span>
            )}
          </Link>
        </div>
      </header>

      {offline && (
        <p className="panel mt-4 p-4 font-mono text-sm text-amber">
          API unreachable — cd backend &amp;&amp; uvicorn memory_shield.api:app --port 8000
        </p>
      )}

      {tab === "today" && (
        <div className="mx-auto mt-6 max-w-3xl space-y-6">
          <section>
            <h1 className="display text-[2.1rem]">
              {greeting}, <span className="serif-accent text-accent">{firstName}</span>.
            </h1>
            <div className="panel mt-4 border-accent/25 bg-accent-soft/20 p-4">
              <p className="label text-accent">today&apos;s signal</p>
              <p className="mt-1.5 text-[15px] font-medium leading-snug">{todayHeadline}</p>
            </div>

            {me && (
              <div className="mt-4">
                <ConnectTelegram compact />
              </div>
            )}

            {overdueIdeas.length > 0 && (
              <div className="panel mt-4 border-amber/30 bg-amber/5 p-4">
                <p className="label text-amber">still on your board</p>
                {overdueIdeas.slice(0, 2).map((idea) => (
                  <div key={idea.id} className="mt-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{idea.title}</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setTab("board");
                          setPitchSeed(`Still worth filming: ${idea.title}`);
                        }}
                        className="font-mono text-[10px] text-accent underline decoration-dotted"
                      >
                        re-check fit →
                      </button>
                      <button
                        onClick={() => setTab("board")}
                        className="font-mono text-[10px] text-dim underline decoration-dotted"
                      >
                        open brief
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section id="concepts">
            <div className="flex items-baseline justify-between">
              <h2 className="display text-[1.35rem]">
                Ready to film
                {activeTrend && (
                  <span className="serif-accent text-accent"> · {activeTrend}</span>
                )}
              </h2>
              <button
                onClick={() => {
                  runSuggest(activeTrend ?? undefined);
                  if (memorySharpened) flash("regenerated with sharpened memory");
                }}
                className="text-xs text-dim underline decoration-dotted underline-offset-4 hover:text-accent"
              >
                regenerate ↻
                {memorySharpened && (
                  <span className="ml-1 text-accent">· memory updated</span>
                )}
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {loading ? (
                <>
                  <p className="font-mono text-xs text-accent">
                    <span className="thinking-dot">●</span> {THINKING[thinkStep]}
                  </p>
                  {[0, 1].map((i) => (
                    <div key={i} className="panel p-5">
                      <div className="skeleton h-4 w-24" />
                      <div className="skeleton mt-3 h-7 w-4/5" />
                      <div className="skeleton mt-2 h-4 w-full" />
                      <div className="skeleton mt-4 h-16 w-full" />
                    </div>
                  ))}
                </>
              ) : (
                visibleCards.map((card, i) => (
                  <ConceptCard
                    key={`${suggestion?.trend}-${i}-${card.title}`}
                    card={card}
                    index={i}
                    selected={selectedCard === i && !pitchTrace}
                    creatorName={lib?.creator.title ?? null}
                    onSelect={() => {
                      setPitchTrace(null);
                      setSelectedCard(i);
                      toggleGraph(true);
                    }}
                    onCreate={async () => {
                      await api.addIdea(
                        card.title,
                        "generated",
                        { card, trace: card.trace, state: "planted" },
                        defaultTarget(),
                      );
                      refreshIdeas();
                      api.garden().then(setGarden).catch(() => {});
                      flash("✨ Created — it's on your board with a target date");
                    }}
                    created={savedTitles.has(card.title)}
                    trace={card.trace}
                    onFeedback={async (confirmed) => {
                      await api.feedback(card.trace, confirmed ? 25 : -25);
                      flash(confirmed ? "Memory sharpened — nailed it" : "Got it — burying that pattern");
                      runSuggest(activeTrend ?? undefined);
                    }}
                  />
                ))
              )}
            </div>
            {!loading && conceptCards.length > 2 && (
              <button
                onClick={() => setShowAllConcepts((v) => !v)}
                className="mt-3 text-xs text-dim underline decoration-dotted underline-offset-4 hover:text-accent"
              >
                {showAllConcepts
                  ? "Show fewer concepts"
                  : `See all ${conceptCards.length} concepts →`}
              </button>
            )}
          </section>

          <details className="panel group p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg hover:text-accent">
              Your garden
              <span className="ml-2 font-mono text-[10px] text-faint">seeds · planted · plants</span>
            </summary>
            <div className="mt-4">
              <SproutDashboard
                garden={garden}
                creatorName={firstName}
                onPlant={handlePlantSeed}
              />
            </div>
          </details>

          <details className="panel group p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg hover:text-accent">
              Channel watch
              {track && (
                <span className="ml-2 font-mono text-[10px] text-faint">
                  {trackedCount} recent uploads
                </span>
              )}
            </summary>
            <div className="mt-4">
              {track && watchHeadline && (
                <>
                  <div className="flex items-center gap-3">
                    <span
                      className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                        underCount === trackedCount ? "bg-amber" : "bg-accent"
                      }`}
                      style={{ boxShadow: "0 0 12px currentColor" }}
                    />
                    <p className="text-sm font-medium leading-snug">{watchHeadline}</p>
                  </div>
                  <ul className="mt-3 space-y-2">
                    {track.uploads.map((u) => (
                      <li key={u.video_id} className="flex items-center gap-3">
                        <Thumb videoId={u.video_id} title={u.title} w={72} />
                        <div className="min-w-0 flex-1">
                          <a
                            href={`https://youtube.com/watch?v=${u.video_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="block truncate text-xs text-fg/90 transition-colors hover:text-accent"
                          >
                            {u.title}
                          </a>
                          <p className="font-mono text-[10px] text-faint">
                            {fmtViews(u.views)} views · {u.age_days}d · {u.ratio}× your median
                            {u.views_delta > 0 && (
                              <span className="text-accent"> · +{fmtViews(u.views_delta)} since last check</span>
                            )}
                          </p>
                        </div>
                        <span
                          className={`shrink-0 font-mono text-[10px] ${UPLOAD_STATUS[u.status].cls}`}
                        >
                          {UPLOAD_STATUS[u.status].label}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {track.improved_nodes > 0 && (
                    <p className="mt-3 border-t border-line pt-2.5 font-mono text-[10px] text-accent">
                      improve(): these numbers already reweighted {track.improved_nodes} memory
                      nodes — you never have to report anything
                    </p>
                  )}
                </>
              )}
              {track && trackedCount === 0 && (
                <p className="text-sm text-faint">
                  Channel watch activates after your first uploads are in the corpus.
                </p>
              )}
            </div>
          </details>

          <details className="panel group p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg hover:text-accent">
              What&apos;s moving in your niche
              <span className="ml-2 font-mono text-[10px] text-faint">{trends.length} waves</span>
            </summary>
            <div className="mt-4">
              <OutlierStrip
                trends={trends}
                activeTrend={activeTrend}
                onPick={(label) => runSuggest(label)}
                onForget={decay}
              />
            </div>
          </details>

          <details className="panel group p-4" id="pitch">
            <summary className="cursor-pointer text-sm font-medium text-fg hover:text-accent">
              Pitch your own idea
              <span className="ml-2 font-mono text-[10px] text-faint">memory pushes back</span>
            </summary>
            <div className="mt-4">
              <PitchBox onTrace={setPitchTrace} onSaved={refreshIdeas} seed={pitchSeed} />
            </div>
          </details>

          <details className="panel group p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg hover:text-accent">
              Skeptic stack
              <span className="ml-2 font-mono text-[10px] text-faint">proof tools</span>
            </summary>
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <button
                onClick={() => setContrastOpen(true)}
                className="text-xs text-dim underline decoration-dotted underline-offset-4 hover:text-accent"
              >
                RAG contrast
              </button>
              <span className="text-faint">·</span>
              <button
                onClick={runBacktest}
                disabled={backtestBusy}
                className="text-xs text-dim underline decoration-dotted underline-offset-4 hover:text-accent disabled:opacity-50"
              >
                sealed backtest
              </button>
              <span className="text-faint">·</span>
              <button
                onClick={() => toggleGraph(true)}
                className="text-xs text-dim underline decoration-dotted underline-offset-4 hover:text-accent"
              >
                show memory graph
              </button>
            </div>
          </details>
        </div>
      )}

      {/* ————— other rooms, one at a time ————— */}
      {tab === "board" && (
        <div className="mx-auto mt-6 max-w-3xl" id="board">
          <IdeasBoard
            ideas={ideas}
            creatorName={lib?.creator.title ?? null}
            onChanged={refreshIdeas}
            onShowGraph={(t) => {
              setPitchTrace(t);
              toggleGraph(true);
            }}
          />
        </div>
      )}

      {tab === "library" && (
        <div className="mt-6">
          {lib ? (
            <ChannelShelf lib={lib} />
          ) : (
            <div className="panel p-5">
              <p className="text-sm text-faint">Library loads after connect — or open the demo Studio.</p>
            </div>
          )}
        </div>
      )}

      {/* ————— the memory: hidden until queried ————— */}
      <aside
        className={`fixed inset-y-0 right-0 z-30 flex w-[min(94vw,30rem)] transform flex-col border-l border-line bg-[#faf4e6]/95 shadow-[-14px_0_40px_-18px_rgba(74,62,34,0.3)] backdrop-blur-md transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          graphOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold tracking-tight">The memory</h2>
            <p className="font-mono text-[10px] text-faint">
              {graph ? `${graph.nodes.length} nodes · ${graph.edges.length} edges` : "loading…"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="max-w-40 truncate text-right font-mono text-[10px] text-dim">
              {pitchTrace
                ? "▸ evidence for your pitch"
                : trace
                  ? `▸ path behind concept ${String((selectedCard ?? 0) + 1).padStart(2, "0")}`
                  : "run a query to trace it"}
            </span>
            <button
              onClick={() => toggleGraph(false)}
              className="text-sm text-faint transition-colors hover:text-fg"
            >
              ✕
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1">
          <GraphPanel graph={graph} trace={trace} querying={graphQuerying} />
        </div>
      </aside>

      {/* queried while the drawer is closed → quiet invitation, not a takeover */}
      {!graphOpen && (pitchTrace || chatGraphPending) && (
        <button
          onClick={() => toggleGraph(true)}
          className="rise panel fixed bottom-4 left-4 z-30 px-4 py-2.5 font-mono text-xs text-accent"
        >
          ⛁ {chatGraphPending ? "memory queried in chat" : "path traced through memory"} — show it
        </button>
      )}

      {backtestBusy && (
        <div className="panel fixed bottom-6 left-1/2 z-50 -translate-x-1/2 px-5 py-2.5 font-mono text-xs text-accent">
          <span className="thinking-dot">●</span> sealed test — suggesting blind, then breaking
          the seal…
        </div>
      )}

      {/* floating strategist */}
      {chatOpen ? (
        <div className="panel fixed bottom-4 right-4 z-40 flex h-[28rem] w-96 flex-col p-4 shadow-2xl">
          <button
            onClick={() => setChatOpen(false)}
            className="absolute right-3 top-2.5 z-10 text-xs text-faint hover:text-fg"
          >
            ▾ minimize
          </button>
          <ChatDock
            onGraphQueryStart={() => setGraphQuerying(true)}
            onGraphQueryEnd={(tools) => {
              setGraphQuerying(false);
              if (touchesGraph(tools) && !graphOpen) {
                setChatGraphPending(true);
              }
              if (touchesGraph(tools)) {
                api.graph().then(setGraph).catch(() => {});
              }
            }}
          />
        </div>
      ) : (
        <button
          onClick={() => setChatOpen(true)}
          className="btn-primary fixed bottom-4 right-4 z-40 px-5 py-3 text-sm"
        >
          🌿 Ask Sprout
        </button>
      )}

      {/* backtest proof — an event, not a section */}
      {backtest && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-[#3a3f2c]/40 p-4 backdrop-blur-sm sm:p-8"
          onClick={() => setBacktest(null)}
        >
          <div className="mx-auto max-w-4xl" onClick={(e) => e.stopPropagation()}>
            <BacktestReveal data={backtest} onClose={() => setBacktest(null)} />
          </div>
        </div>
      )}

      {contrastOpen && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-[#3a3f2c]/40 p-4 backdrop-blur-sm sm:p-8"
          onClick={() => setContrastOpen(false)}
        >
          <div className="mx-auto max-w-4xl" onClick={(e) => e.stopPropagation()}>
            <RagContrast trend={activeTrend} onClose={() => setContrastOpen(false)} />
          </div>
        </div>
      )}

      {toast && (
        <div className="rise panel fixed bottom-6 left-1/2 z-50 -translate-x-1/2 px-5 py-2.5 font-mono text-xs text-accent">
          {toast}
        </div>
      )}

      <CoachMarks skip={search.get("proof") === "1"} />
      </main>
    </>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={null}>
      <Studio />
    </Suspense>
  );
}

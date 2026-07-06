"use client";

/* The core loop, animated — because the loop IS the product:
   analytics drip in (remember) → one memory of you → recall() joins it with
   the live niche → a cited card → your one-tap reaction → improve()/forget()
   → back into the memory, sharper. A pulse travels the loop forever; each
   completed lap visibly sharpens the memory (weights thicken, receipts hold).
   Sharper, not bigger. */

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "motion/react";
import {
  Cognee,
  Firebase,
  HackerNews,
  OpenAI,
  Python,
  Reddit,
  Telegram,
  YouTube,
} from "@/components/BrandLogos";
import { DashboardGlyph, LOOP_OPS } from "@/components/SproutGlyphs";

const CYCLE = 11; // seconds per lap

/* pulse waypoints through the loop (viewBox 0 0 960 430) */
const PULSE = {
  cx: [350, 590, 830, 838, 720, 590, 350, 252, 332, 350],
  cy: [115, 115, 115, 172, 296, 308, 308, 226, 136, 115],
  times: [0, 0.16, 0.32, 0.4, 0.5, 0.56, 0.74, 0.84, 0.95, 1],
};

/* when the pulse reaches each station (fraction of a lap) */
const AT = { memory: 0.0, join: 0.16, card: 0.32, tap: 0.56, tend: 0.74 };

/* a station's soft glow, timed to the pulse passing */
function Glow({ at }: { at: number }) {
  const t = (d: number) => Math.min(Math.max(at + d, 0), 1);
  return (
    <motion.span
      className="pointer-events-none absolute -inset-1 rounded-2xl"
      style={{ boxShadow: "0 0 0 1.5px rgba(93,138,69,0.55), 0 8px 30px rgba(93,138,69,0.25)" }}
      initial={{ opacity: 0 }}
      animate={{ opacity: [0, 0, 1, 0, 0] }}
      transition={{
        duration: CYCLE,
        times: [0, t(-0.03), t(0.015), t(0.09), 1],
        repeat: Infinity,
        ease: "easeOut",
      }}
    />
  );
}

const ICON_MAP = {
  youtube: YouTube,
  firebase: Firebase,
  cognee: Cognee,
  python: Python,
  hn: HackerNews,
  reddit: Reddit,
  openai: OpenAI,
  telegram: Telegram,
  dashboard: DashboardGlyph,
} as const;

type IconKey = keyof typeof ICON_MAP;

function StationIcons({ keys }: { keys: readonly IconKey[] }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-[color:var(--line-2)] pt-1.5">
      {keys.map((k) => {
        const Ico = ICON_MAP[k];
        return (
          <span
            key={k}
            className="grid h-5 w-5 place-items-center rounded-md bg-[color:var(--card-2)]"
            title={k}
          >
            <Ico className="h-3.5 w-3.5" />
          </span>
        );
      })}
    </div>
  );
}

function Station({
  x,
  y,
  w = 168,
  at,
  label,
  op,
  iconKeys,
  children,
}: {
  x: number;
  y: number;
  w?: number;
  at?: number;
  label: string;
  op?: string;
  iconKeys?: readonly IconKey[];
  children: React.ReactNode;
}) {
  return (
    <div
      className="absolute -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${(x / 960) * 100}%`, top: `${(y / 430) * 100}%`, width: w }}
    >
      <div className="relative rounded-2xl border border-[color:var(--line)] bg-[color:var(--card)] p-2.5 shadow-[0_1px_2px_rgba(74,62,34,0.05),0_10px_30px_-14px_rgba(74,62,34,0.25)]">
        {at !== undefined && <Glow at={at} />}
        <p className="mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--moss-deep)]">
          {label}
        </p>
        <div className="mt-1.5">{children}</div>
        {iconKeys && iconKeys.length > 0 && <StationIcons keys={iconKeys} />}
      </div>
      {op && (
        <p className="mono mt-1.5 text-center text-[9px] text-[color:var(--ink-faint)]">{op}</p>
      )}
    </div>
  );
}

/* the memory as a tiny root-graph; edges thicken as the memory sharpens */
function MemoryGraph({ sharp }: { sharp: number }) {
  const N = [
    { x: 38, y: 10, c: "#b45f35", l: "you" },
    { x: 12, y: 30, c: "#e0a53a", l: "hooks" },
    { x: 40, y: 40, c: "#cf7c4c", l: "formats" },
    { x: 68, y: 28, c: "#5d8a45", l: "topics" },
    { x: 88, y: 44, c: "#7fb0c9", l: "trends" },
  ];
  const E: [number, number][] = [
    [0, 1],
    [0, 2],
    [0, 3],
    [3, 4],
    [1, 2],
    [2, 3],
  ];
  return (
    <svg viewBox="0 0 100 52" className="w-full">
      {E.map(([a, b], i) => (
        <line
          key={i}
          x1={N[a].x}
          y1={N[a].y}
          x2={N[b].x}
          y2={N[b].y}
          stroke="#5d8a45"
          strokeWidth={0.8 + sharp * 0.55}
          strokeOpacity={0.35 + sharp * 0.18}
          style={{ transition: "stroke-width 1.2s ease, stroke-opacity 1.2s ease" }}
        />
      ))}
      {N.map((n) => (
        <circle key={n.l} cx={n.x} cy={n.y} r={n.l === "you" ? 4 : 3} fill={n.c} />
      ))}
    </svg>
  );
}

export default function CoreLoop() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: false, margin: "-80px" });
  const [lap, setLap] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const id = setInterval(() => setLap((l) => l + 1), CYCLE * 1000);
    return () => clearInterval(id);
  }, [inView]);

  const sharp = Math.min(lap, 3); // visual sharpening caps, honestly

  return (
    <div ref={ref} className="card overflow-hidden">
      <div className="overflow-x-auto">
        <div className="relative mx-auto aspect-[960/430] min-w-[860px] max-w-[1020px]">
          {/* ── connectors + pulse (SVG layer) ── */}
          <svg viewBox="0 0 960 430" className="absolute inset-0 h-full w-full" fill="none">
            <defs>
              <marker id="cl-arrow" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0 0 L8 4 L0 8 Z" fill="#5d8a45" fillOpacity="0.55" />
              </marker>
            </defs>

            {/* analytics inlet — remember(), always dripping */}
            <path d="M 168 115 C 220 115 250 115 288 115" className="cl-flow" markerEnd="url(#cl-arrow)" />
            {/* memory → join → card */}
            <path d="M 412 115 C 470 115 490 115 526 115" className="cl-flow" markerEnd="url(#cl-arrow)" />
            <path d="M 654 115 C 710 115 728 115 764 115" className="cl-flow" markerEnd="url(#cl-arrow)" />
            {/* card ↓ one-tap */}
            <path d="M 834 168 C 838 236 748 300 662 306" className="cl-flow" markerEnd="url(#cl-arrow)" />
            {/* one-tap → tend */}
            <path d="M 518 308 C 480 308 460 308 424 308" className="cl-flow" markerEnd="url(#cl-arrow)" />
            {/* tend ↺ memory — the lap that sharpens */}
            <path d="M 286 296 C 220 270 218 160 292 130" className="cl-flow" markerEnd="url(#cl-arrow)" />

            {/* analytics droplets feeding the memory (nightly, incremental) */}
            {[0, 0.9, 1.8].map((d) => (
              <motion.circle
                key={d}
                r="3"
                cy={115}
                fill="#7fb0c9"
                initial={{ opacity: 0 }}
                animate={{ cx: [176, 284], opacity: [0, 0.9, 0.9, 0] }}
                transition={{ duration: 2.6, delay: d, repeat: Infinity, ease: "easeIn", times: [0, 0.15, 0.85, 1] }}
              />
            ))}

            {/* THE pulse — one suggestion making a full lap */}
            {inView && (
              <>
                <motion.circle
                  r="7"
                  fill="#5d8a45"
                  fillOpacity="0.25"
                  animate={{ cx: PULSE.cx, cy: PULSE.cy }}
                  transition={{ duration: CYCLE, times: PULSE.times, repeat: Infinity, ease: "easeInOut" }}
                />
                <motion.circle
                  r="3.5"
                  fill="#3f6a32"
                  animate={{ cx: PULSE.cx, cy: PULSE.cy }}
                  transition={{ duration: CYCLE, times: PULSE.times, repeat: Infinity, ease: "easeInOut" }}
                />
              </>
            )}
          </svg>

          {/* ── stations (HTML layer) ── */}
          <Station x={110} y={115} w={150} label="your analytics" op="private · OAuth, read-only" iconKeys={["youtube", "firebase"]}>
            <svg viewBox="0 0 100 34" className="w-full" fill="none">
              {[12, 34, 56, 78].map((x, i) => (
                <rect key={x} x={x} y={30 - [8, 13, 6, 11][i]} width="7" height={[8, 13, 6, 11][i]} rx="1.5" fill="#5d8a45" fillOpacity="0.55" />
              ))}
              {/* retention curve over the bars */}
              <path d="M4 8 C 22 10 30 20 48 22 C 66 24 80 25 96 26" stroke="#cf7c4c" strokeWidth="1.8" strokeLinecap="round" />
              <circle cx="96" cy="26" r="2.2" fill="#cf7c4c" />
            </svg>
            <p className="mono mt-1 text-[8.5px] text-[color:var(--ink-faint)]">retention · CTR · traffic · subs</p>
          </Station>

          <Station x={350} y={115} w={170} at={AT.memory} label="one memory of you" op="pattern-nodes, weighted" iconKeys={["cognee"]}>
            <MemoryGraph sharp={sharp} />
            {/* feedback_weight bars — these are what sharpen */}
            <div className="mt-1.5 space-y-1">
              {[
                ["hook", 34],
                ["format", 26],
                ["topic", 42],
              ].map(([l, base]) => (
                <div key={l} className="flex items-center gap-1.5">
                  <span className="mono w-9 text-[7.5px] text-[color:var(--ink-faint)]">{l}</span>
                  <span className="h-1 flex-1 rounded-full bg-[color:var(--moss-a12)]">
                    <span
                      className="block h-1 rounded-full bg-gradient-to-r from-[color:var(--moss)] to-[color:var(--moss-deep)]"
                      style={{ width: `${Math.min((base as number) + sharp * 16, 96)}%`, transition: "width 1.2s ease" }}
                    />
                  </span>
                </div>
              ))}
            </div>
          </Station>

          <Station x={590} y={115} w={170} at={AT.join} label="recall() — the join" op="multi-hop graph query, not one search()" iconKeys={["cognee", "python", "hn", "reddit"]}>
            <p className="text-[10.5px] leading-snug text-[color:var(--ink)]">
              what converts <em className="ital">for you</em>
              <span className="mx-1 text-[color:var(--moss-deep)]">×</span> live trends
              <span className="mx-1 text-[color:var(--moss-deep)]">×</span> true competitors
            </p>
            <p className="mono mt-1.5 text-[8.5px] text-[color:var(--ink-faint)]">
              size band 0.3×–10× yours · semantic hop, not keywords
            </p>
          </Station>

          <Station x={834} y={115} w={172} at={AT.card} label="a card, with receipts" iconKeys={["python", "openai"]}>
            <p className="text-[11px] font-semibold leading-tight text-[color:var(--ink)]">
              Why your RAG demo flopped
            </p>
            <p className="ital mt-0.5 text-[9.5px] text-[color:var(--ink-soft)]">
              “the eval nobody runs…”
            </p>
            <div className="mt-1.5 flex items-center gap-1.5">
              <span className="art art-dawn h-6 w-10 rounded" />
              <span className="art art-forest h-6 w-10 rounded" />
              <span className="mono whitespace-nowrap rounded-full bg-[color:var(--moss-a12)] px-1.5 py-0.5 text-[8px] font-medium text-[color:var(--moss-deep)]">
                2.1× CTR · n=5
              </span>
            </div>
            <p className="mono mt-1 text-[8px] text-[color:var(--ink-faint)]">every number computed, never guessed</p>
          </Station>

          <Station x={590} y={308} w={182} at={AT.tap} label="you, one tap" op="that's the whole job" iconKeys={["telegram", "dashboard"]}>
            <div className="flex gap-1.5">
              <span className="relative whitespace-nowrap rounded-full border border-[color:var(--moss-a40)] bg-[color:var(--moss-a12)] px-2 py-1 text-[9.5px] font-medium text-[color:var(--moss-deep)]">
                👍 nailed it
                {/* the tap ripple, timed to the pulse */}
                <motion.span
                  className="pointer-events-none absolute inset-0 rounded-full border-2 border-[color:var(--moss)]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 0, 0.9, 0], scale: [1, 1, 1.25, 1.45] }}
                  transition={{ duration: CYCLE, times: [0, 0.57, 0.62, 0.7], repeat: Infinity }}
                />
              </span>
              <span className="whitespace-nowrap rounded-full border border-[color:var(--line)] px-2 py-1 text-[9.5px] text-[color:var(--ink-soft)]">
                👎 you&apos;re wrong
              </span>
            </div>
          </Station>

          <Station x={350} y={308} w={172} at={AT.tend} label="tend & compost" iconKeys={["cognee"]}>
            <div className="space-y-1 text-[10px] leading-snug">
              <p>
                <span className="mono text-[9px] text-[color:var(--moss-deep)]">improve()</span>{" "}
                <span className="text-[color:var(--ink-soft)]">reweights that hook + format + topic</span>
              </p>
              <p>
                <span className="mono text-[9px] text-[color:var(--clay)]">forget()</span>{" "}
                <span className="text-[color:var(--ink-soft)]">composts stale trends & dead seeds</span>
              </p>
            </div>
          </Station>

          {/* ── the lap counter — the point of the whole diagram ── */}
          <div className="absolute left-1/2 top-[52%] w-56 -translate-x-1/2 -translate-y-1/2 text-center">
            <p className="ital text-[17px] leading-snug text-[color:var(--moss-deep)]">
              same memory,
              <br />
              sharper every lap
            </p>
            <p className="mono mt-1.5 text-[10px] text-[color:var(--ink-faint)]">
              lap {lap + 1}
              {sharp > 0 && (
                <span className="text-[color:var(--moss-deep)]"> · weights ↑{sharp}</span>
              )}
            </p>
          </div>

          {/* return-arc caption */}
          <p
            className="mono absolute text-[8.5px] text-[color:var(--ink-faint)]"
            style={{ left: "17.5%", top: "48%" }}
          >
            ↺ sharper
            <br />
            next lap
          </p>
          {/* inlet caption */}
          <p className="mono absolute text-[8.5px] text-[color:var(--ink-faint)]" style={{ left: "19%", top: "31.5%" }}>
            remember() · nightly
          </p>
        </div>
      </div>

      {/* four Cognee ops — the gardener's moves that drive the loop */}
      <div className="border-t border-[color:var(--line-2)] bg-[color:var(--card-2)]/50 px-4 py-4">
        <p className="label mb-3 text-center">four ops underneath · sharper every lap</p>
        <div className="mx-auto flex max-w-3xl flex-wrap items-start justify-center gap-6 sm:gap-10">
          {LOOP_OPS.map((op) => (
            <div key={op.key} className="flex flex-col items-center gap-1.5 text-center">
              <span className="grid h-9 w-9 place-items-center rounded-xl border border-[color:var(--line)] bg-[color:var(--card)] shadow-sm">
                {op.glyph}
              </span>
              <span className="mono text-[10px] font-medium uppercase tracking-widest text-[color:var(--moss-deep)]">
                {op.key}()
              </span>
              <span className="max-w-[7rem] text-[9px] leading-snug text-[color:var(--ink-faint)]">{op.hint}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

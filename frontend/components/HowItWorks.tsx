"use client";

/* The whole product flow — scroll-driven steps with animated viz panels
   (signal → analysis → graph → surfaces → steer). Living gouache behind. */

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import {
  Cognee,
  Firebase,
  LogoChip,
  OpenAI,
  Python,
  Reddit,
  Telegram,
  YouTube,
} from "@/components/BrandLogos";
import LivingPainting from "@/components/LivingPainting";

const EASE = [0.16, 0.8, 0.3, 1] as const;

type Stage = {
  key: string;
  name: string;
  body: string;
  chips: string[];
  Viz: React.ComponentType<{ active: boolean }>;
};

/* ——— step visualizations (warm Sprout palette, reference-style motion) ——— */

function VizPanel({
  active,
  children,
  className = "",
}: {
  active: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 28, scale: 0.97 }}
      animate={active ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0.35, y: 12, scale: 0.98 }}
      transition={{ duration: 0.7, ease: EASE }}
      className={`hiw-viz relative overflow-hidden rounded-2xl border border-[color:var(--line)] bg-[color:var(--card)]/80 p-5 shadow-[var(--shadow)] backdrop-blur-sm ${className}`}
    >
      {children}
    </motion.div>
  );
}

function Viz01({ active }: { active: boolean }) {
  return (
    <VizPanel active={active}>
      <svg viewBox="0 0 400 160" className="w-full" fill="none">
        <motion.path
          d="M 20 95 Q 70 40, 120 72 T 220 58 T 320 78 T 380 52"
          stroke="var(--moss)"
          strokeWidth="2.2"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={active ? { pathLength: 1, opacity: 1 } : { pathLength: 0.3, opacity: 0.4 }}
          transition={{ duration: 1.4, ease: EASE }}
        />
        <motion.path
          d="M 20 95 Q 70 40, 120 72 T 220 58 T 320 78 T 380 52"
          stroke="var(--moss)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeOpacity="0.12"
          initial={{ pathLength: 0 }}
          animate={active ? { pathLength: 1 } : { pathLength: 0.3 }}
          transition={{ duration: 1.4, ease: EASE }}
        />
        <motion.g
          initial={{ opacity: 0, y: -8 }}
          animate={active ? { opacity: 1, y: [0, -4, 0] } : { opacity: 0.3, y: 0 }}
          transition={active ? { opacity: { duration: 0.5 }, y: { duration: 3.2, repeat: Infinity, ease: "easeInOut" } } : { duration: 0.4 }}
        >
          <rect x="148" y="18" width="104" height="28" rx="14" fill="var(--moss-a15)" stroke="var(--moss-a40)" strokeWidth="1.2" />
          <text x="200" y="36" textAnchor="middle" fill="var(--moss-deep)" style={{ font: "500 10px var(--font-jetbrains)", letterSpacing: "0.06em" }}>
            OAuth · read-only
          </text>
          {active && (
            <motion.rect
              x="148" y="18" width="104" height="28" rx="14"
              stroke="var(--moss)"
              strokeWidth="1.5"
              fill="none"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ duration: 2.4, repeat: Infinity }}
            />
          )}
        </motion.g>
        {[
          { x: 72, label: "YouTube", color: "#cf7c4c" },
          { x: 168, label: "News", color: "#cf7c4c" },
          { x: 264, label: "Reddit", color: "#e08aa0" },
        ].map((ic, i) => (
          <motion.g
            key={ic.label}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={active ? { opacity: 1, scale: 1 } : { opacity: 0.25, scale: 0.85 }}
            transition={{ delay: 0.2 + i * 0.12, duration: 0.5, ease: EASE }}
          >
            <circle cx={ic.x} cy="128" r="22" fill="var(--card-2)" stroke="var(--line)" />
            <circle cx={ic.x} cy="128" r="26" fill="none" stroke={ic.color} strokeOpacity="0.35" strokeWidth="1" />
            <text x={ic.x} y="132" textAnchor="middle" fill="var(--ink-soft)" style={{ font: "500 9px var(--font-jetbrains)" }}>
              {ic.label}
            </text>
          </motion.g>
        ))}
        <text x="200" y="155" textAnchor="middle" fill="var(--ink-faint)" style={{ font: "500 9px var(--font-jetbrains)", letterSpacing: "0.1em" }}>
          retention · CTR · traffic · subs
        </text>
      </svg>
    </VizPanel>
  );
}

function Viz02({ active }: { active: boolean }) {
  const metrics = [
    { label: "CTR vs median", val: "→ 2.1×", pos: "left-[5%] top-[7%] w-[56%]", z: "z-10", delay: 0 },
    { label: "effect_size", val: "0.34 · n=12", pos: "left-[24%] top-[33%] w-[60%]", z: "z-30", delay: 0.12 },
    { label: "rank_by", val: "growth_score ↓", pos: "left-[7%] top-[57%] w-[50%]", z: "z-20", delay: 0.24 },
  ];
  return (
    <VizPanel active={active} className="hiw-viz-pipeline !border-white/60 !bg-white/55 !p-4 sm:!p-5">
      <div className="hiw-pipeline-stage relative mx-auto aspect-[17/10] max-w-[340px]">
        <div
          aria-hidden
          className="pointer-events-none absolute -inset-1 rounded-[22px] bg-gradient-to-br from-[rgba(238,243,232,0.9)] via-[rgba(253,247,242,0.5)] to-[rgba(253,242,240,0.85)]"
        />
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.96 }}
          animate={active ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0.35, y: 10, scale: 0.98 }}
          transition={{ duration: 0.7, ease: EASE }}
          className="absolute inset-x-0 inset-y-1"
        >
          <div className={`hiw-pipeline-card relative h-full rounded-[20px] border border-white/80 bg-white/95 shadow-[0_10px_40px_-12px_rgba(74,62,34,0.16),0_2px_6px_-1px_rgba(74,62,34,0.06)] ${active ? "float" : ""}`}>
          {metrics.map((m) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, x: -14, y: 10 }}
              animate={active ? { opacity: 1, x: 0, y: 0 } : { opacity: 0.18, x: -8, y: 6 }}
              transition={{ delay: m.delay, duration: 0.55, ease: EASE }}
              className={`absolute ${m.pos} ${m.z} rounded-xl border border-[color:var(--line)]/80 bg-[color:var(--card)] px-3.5 py-2.5 shadow-[0_6px_18px_-8px_rgba(74,62,34,0.14),inset_0_1px_0_rgba(255,255,255,0.9)]`}
            >
              <p className="mono text-[8px] tracking-[0.12em] text-[color:var(--ink-faint)] uppercase">{m.label}</p>
              <p className="mono mt-1 text-[13px] font-semibold leading-none text-[color:var(--ink)]">{m.val}</p>
            </motion.div>
          ))}
          <motion.div
            initial={{ opacity: 0, scale: 0.88, y: -6 }}
            animate={active ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0.2, scale: 0.94 }}
            transition={{ delay: 0.32, duration: 0.5, ease: EASE }}
            className="absolute right-[4%] top-[5%] z-40 rounded-[10px] border border-[rgba(200,230,201,0.9)] bg-[rgba(232,245,233,0.95)] px-3 py-2 shadow-[0_4px_12px_-6px_rgba(93,138,69,0.25)]"
          >
            <p className="mono text-[10px] font-semibold text-[color:var(--moss-deep)]">gpt-4o-mini</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.88, y: 6 }}
            animate={active ? { opacity: 1, scale: 1, y: 0 } : { opacity: 0.2, scale: 0.94 }}
            transition={{ delay: 0.42, duration: 0.5, ease: EASE }}
            className="absolute right-[3%] bottom-[22%] z-40 rounded-[10px] border border-[rgba(255,224,178,0.95)] bg-[rgba(255,243,224,0.96)] px-3 py-2 shadow-[0_4px_12px_-6px_rgba(207,124,76,0.22)]"
          >
            <p className="mono text-[10px] font-semibold text-[color:var(--clay)]">Python</p>
          </motion.div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={active ? { opacity: 1 } : { opacity: 0.25 }}
            transition={{ delay: 0.5, duration: 0.45 }}
            className="mono absolute inset-x-0 bottom-2.5 text-center text-[7px] tracking-[0.16em] text-[color:var(--ink-faint)]"
          >
            NUMBERS NEVER GUESSED
          </motion.p>
          </div>
        </motion.div>
      </div>
    </VizPanel>
  );
}

const GRAPH_NODES = [
  { x: 60, y: 80, c: "#e0a53a", l: "hooks" },
  { x: 140, y: 50, c: "#cf7c4c", l: "formats" },
  { x: 220, y: 75, c: "#6b96f2", l: "topics" },
  { x: 300, y: 55, c: "#4e9e6f", l: "trends" },
  { x: 340, y: 110, c: "#a06bd6", l: "rivals" },
  { x: 180, y: 120, c: "#5d8a45", l: "you" },
];
const GRAPH_EDGES: [number, number][] = [[5, 0], [5, 1], [5, 2], [2, 3], [1, 4], [0, 2]];

function Viz03({ active }: { active: boolean }) {
  return (
    <VizPanel active={active}>
      <svg viewBox="0 0 400 150" className="w-full" fill="none">
        {GRAPH_EDGES.map(([a, b], i) => (
          <motion.line
            key={i}
            x1={GRAPH_NODES[a].x} y1={GRAPH_NODES[a].y}
            x2={GRAPH_NODES[b].x} y2={GRAPH_NODES[b].y}
            stroke="var(--moss)"
            strokeOpacity="0.45"
            strokeWidth="1.5"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={active ? { pathLength: 1, opacity: 1 } : { pathLength: 0.2, opacity: 0.2 }}
            transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: EASE }}
          />
        ))}
        {GRAPH_NODES.map((n, i) => (
          <motion.g
            key={n.l}
            initial={{ scale: 0, opacity: 0 }}
            animate={active ? { scale: 1, opacity: 1 } : { scale: 0.5, opacity: 0.25 }}
            transition={{ delay: 0.05 + i * 0.1, type: "spring", stiffness: 200, damping: 16 }}
          >
            <circle cx={n.x} cy={n.y} r="14" fill={n.c} fillOpacity="0.25" stroke={n.c} strokeWidth="1.5" />
            <text x={n.x} y={n.y + 4} textAnchor="middle" fill="var(--ink-soft)" style={{ font: "500 8px var(--font-jetbrains)" }}>
              {n.l}
            </text>
          </motion.g>
        ))}
        {active && (
          <motion.circle
            r="5"
            fill="var(--moss)"
            initial={{ opacity: 0 }}
            animate={{
              opacity: [0, 1, 1, 0],
              cx: [60, 140, 220, 300, 180],
              cy: [80, 50, 75, 55, 120],
            }}
            transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
        <text x="200" y="145" textAnchor="middle" fill="var(--ink-faint)" style={{ font: "500 9px var(--font-jetbrains)", letterSpacing: "0.1em" }}>
          my_channel · competitors · trends · drafts
        </text>
      </svg>
    </VizPanel>
  );
}

function Viz04({ active }: { active: boolean }) {
  return (
    <VizPanel active={active}>
      <div className="grid h-[140px] grid-cols-2 gap-2">
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={active ? { opacity: 1, x: 0 } : { opacity: 0.3 }}
          className="overflow-hidden rounded-xl border border-[color:var(--line)] bg-[color:var(--card-2)] p-2"
        >
          <p className="mono text-[8px] text-[color:var(--ink-faint)]">dashboard</p>
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={active ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="mt-1.5 rounded-lg border border-[color:var(--moss-a25)] bg-[color:var(--moss-a08)] p-1.5"
          >
            <p className="text-[9px] leading-snug text-[color:var(--ink)]">3 planted · 4 seeds waiting</p>
          </motion.div>
          <div className="mt-1.5 grid grid-cols-2 gap-1">
            {[0, 1].map((i) => (
              <motion.div
                key={i}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={active ? { scale: 1, opacity: 1 } : {}}
                transition={{ delay: 0.35 + i * 0.1 }}
                className="art art-meadow h-8 rounded-md"
              />
            ))}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={active ? { opacity: 1, x: 0 } : { opacity: 0.3 }}
          transition={{ delay: 0.1 }}
          className="flex flex-col justify-end"
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.94 }}
            animate={active ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0.2 }}
            transition={{ delay: 0.4, type: "spring", stiffness: 160, damping: 18 }}
            className="rounded-xl rounded-br-sm border border-[color:var(--line)] bg-white p-2 shadow-sm"
          >
            <p className="mono text-[7px] text-[color:var(--ink-faint)]">telegram · now</p>
            <p className="mt-1 text-[9px] leading-snug text-[color:var(--ink)]">Beat median retention 🎉</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={active ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.65, type: "spring" }}
            className="mt-1.5 rounded-xl rounded-br-sm border border-[color:var(--line)] bg-white p-2 shadow-sm"
          >
            <p className="mono text-[7px] text-[color:var(--ink-faint)]">telegram · 2m ago</p>
            <p className="mt-1 text-[9px] leading-snug text-[color:var(--ink)]">Plant the RAG seed?</p>
          </motion.div>
        </motion.div>
      </div>
      <motion.p
        className="mono mt-2 text-center text-[8px] tracking-widest text-[color:var(--ink-faint)]"
        animate={active ? { opacity: [0.4, 1, 0.4] } : { opacity: 0.3 }}
        transition={{ duration: 2.5, repeat: Infinity }}
      >
        one memory underneath both
      </motion.p>
    </VizPanel>
  );
}

function Viz05({ active }: { active: boolean }) {
  return (
    <VizPanel active={active}>
      <div className="space-y-2">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={active ? { opacity: 1, y: 0 } : { opacity: 0.25 }}
          className="rounded-xl border border-[color:var(--line)] bg-white p-2"
        >
          <p className="text-[10px] text-[color:var(--ink)]">People slip at 0:40 — want two hooks?</p>
          <div className="mt-2 flex gap-1">
            {["nailed it", "tweak", "wrong"].map((b, i) => (
              <motion.span
                key={b}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={active ? { scale: 1, opacity: 1 } : {}}
                transition={{ delay: 0.2 + i * 0.08 }}
                className={`rounded-full px-2 py-0.5 text-[9px] ${
                  i === 0 && active
                    ? "bg-[color:var(--moss)] font-medium text-white shadow-sm"
                    : "border border-[color:var(--line)] text-[color:var(--ink-soft)]"
                }`}
              >
                {b}
              </motion.span>
            ))}
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={active ? { opacity: 1 } : { opacity: 0.2 }}
          transition={{ delay: 0.5 }}
          className="rounded-lg border border-[color:var(--moss-a40)] bg-[color:var(--moss-a08)] px-2 py-1.5"
        >
          <p className="mono text-[9px] text-[color:var(--moss-deep)]">improve() · hook + format + topic ↑</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={active ? { opacity: 1 } : { opacity: 0.2 }}
          transition={{ delay: 0.7 }}
          className="rounded-lg border border-dashed border-[color:var(--clay)]/40 bg-[color:var(--clay-a12)] px-2 py-1.5"
        >
          <p className="mono text-[9px] text-[color:var(--clay)]">forget() · trends_2026_w12 composted</p>
        </motion.div>
      </div>
    </VizPanel>
  );
}

const STAGES: Stage[] = [
  {
    key: "01",
    name: "Your world",
    body: "Your private analytics — retention, CTR, traffic, subs — via one-click OAuth, plus what your niche is actually doing right now.",
    chips: ["OAuth · read-only", "live niche"],
    Viz: Viz01,
  },
  {
    key: "02",
    name: "Honest analysis",
    body: "Python does every number — comparisons, effect sizes, ranking. gpt-4o-mini turns messy text into clean labels; one vision call reads each thumbnail. Numbers are never guessed.",
    chips: ["Python = math", "LLM = words"],
    Viz: Viz02,
  },
  {
    key: "03",
    name: "One memory of you",
    body: "It all becomes one hybrid graph — your hooks, formats and topics joined to live trends and true rivals, tagged with the patterns we computed. Cognee remembers them; it never invents them.",
    chips: ["my_channel", "competitors", "trends", "drafts"],
    Viz: Viz03,
  },
  {
    key: "04",
    name: "Two surfaces, one brain",
    body: "The garden dashboard for deliberate, visual work; a Telegram bot for ambient nudges, celebrations and quick-capture. One memory underneath both.",
    chips: ["dashboard", "telegram"],
    Viz: Viz04,
  },
  {
    key: "05",
    name: "You steer it",
    body: "Yes / no / tweak. improve() strengthens the hook + format + topic that convert for you; forget() composts stale trends. The next suggestion is measurably sharper.",
    chips: ["improve()", "forget()"],
    Viz: Viz05,
  },
];

function StepRow({ stage, index }: { stage: Stage; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const active = useInView(ref, { margin: "-35% 0px -35% 0px", amount: 0.4 });
  const flip = index % 2 === 1;
  const { Viz } = stage;

  return (
    <div
      ref={ref}
      className={`hiw-step grid min-h-[min(72vh,560px)] items-center gap-10 py-10 lg:grid-cols-2 lg:gap-16 lg:py-14 ${flip ? "lg:[&>*:first-child]:order-2" : ""}`}
    >
      <motion.div
        initial={{ opacity: 0, x: flip ? 24 : -24 }}
        animate={active ? { opacity: 1, x: 0 } : { opacity: 0.35, x: flip ? 12 : -12 }}
        transition={{ duration: 0.65, ease: EASE }}
      >
        <span
          className={`display leading-none text-[color:var(--moss-a25)] ${
            stage.key === "02" ? "text-[clamp(4rem,10vw,6.5rem)]" : "text-[clamp(3.5rem,8vw,5.5rem)]"
          }`}
        >
          {stage.key}
        </span>
        <p className="label mt-2">{stage.key} · pipeline</p>
        <h3 className="display mt-3 text-2xl sm:text-3xl">{stage.name}</h3>
        <p className="mt-3 max-w-md text-[15px] leading-relaxed text-[color:var(--ink-soft)]">{stage.body}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {stage.chips.map((c) => (
            <span key={c} className="chip !text-[10px]">{c}</span>
          ))}
        </div>
      </motion.div>
      <Viz active={active} />
    </div>
  );
}

export default function HowItWorks() {
  return (
    <section id="pipeline" className="hiw-section relative mt-28 overflow-hidden sm:mt-36">
      <div className="pointer-events-none absolute inset-0">
        <LivingPainting />
        <div className="absolute inset-0 bg-gradient-to-b from-[color:var(--paper)]/30 via-transparent to-[color:var(--paper)]/50" />
      </div>

      <div className="relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-70px" }}
          transition={{ duration: 0.6, ease: EASE }}
          className="max-w-2xl"
        >
          <p className="label">under the soil</p>
          <h2 className="display mt-3 text-3xl sm:text-4xl">
            The whole loop, <span className="ital text-[color:var(--moss-deep)]">start to sharper.</span>
          </h2>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[color:var(--ink-soft)]">
            Nothing here a chat window could fake — real private numbers, a live niche graph, and a
            memory that compounds. Here’s exactly how a scroll becomes a cited idea.
          </p>
        </motion.div>

        <div className="mt-8 lg:mt-4">
          {STAGES.map((s, i) => (
            <StepRow key={s.key} stage={s} index={i} />
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="mt-2 flex items-center gap-3"
        >
          <span className="h-px flex-1" style={{ backgroundImage: "repeating-linear-gradient(90deg, var(--line) 0 6px, transparent 6px 12px)" }} />
          <span className="chip !border-[color:var(--moss-a40)] !bg-[color:var(--moss-a08)] !text-[color:var(--moss-deep)]">
            ↺ and it compounds — every reaction makes next week’s idea more yours
          </span>
          <span className="h-px flex-1" style={{ backgroundImage: "repeating-linear-gradient(90deg, var(--line) 0 6px, transparent 6px 12px)" }} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.55 }}
          className="mt-16"
        >
          <p className="label text-center">built with</p>
          <div className="mt-6 flex flex-wrap justify-center gap-2.5">
            <LogoChip logo={<Cognee className="h-6 w-6" />} label="Cognee" sub="memory graph" />
            <LogoChip logo={<YouTube className="h-6 w-6" />} label="YouTube" sub="data + analytics" />
            <LogoChip logo={<Telegram className="h-6 w-6" />} label="Telegram" sub="bot surface" />
            <LogoChip logo={<OpenAI className="h-6 w-6" />} label="OpenAI" sub="gpt-4o-mini" />
            <LogoChip logo={<Reddit className="h-6 w-6" />} label="Reddit" sub="discourse radar" />
            <LogoChip logo={<Python className="h-6 w-6" />} label="Python" sub="pandas · numpy" />
            <LogoChip logo={<Firebase className="h-6 w-6" />} label="Firebase" sub="one-click auth" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

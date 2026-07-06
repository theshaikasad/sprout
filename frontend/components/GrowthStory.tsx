"use client";

/* Scroll-pinned growth story — garden fills the whole viewport; copy on the left sky. */

import { useRef, useState } from "react";
import {
  motion,
  useMotionValueEvent,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from "motion/react";
import { GardenPlant } from "@/components/GardenScene";

const BEATS = [
  {
    tag: "01 · connect",
    dot: "🌱",
    title: "It learns what you are",
    body: "Connect YouTube once. Sprout reads your last 40 videos — weighted by what actually converts — and names your genre back to you. No niche dropdown to guess at.",
    note: "reads retention · CTR · traffic",
  },
  {
    tag: "02 · recall",
    dot: "🌿",
    title: "Cited concept cards",
    body: "Ideas take root as cards — title, hook, thumbnail concept — each element citing a pattern that converted for you. Not a prompt into the void. A graph traversal.",
    note: "cites 5 vids · 2.1× CTR",
  },
  {
    tag: "03 · reframe",
    dot: "🍃",
    title: "Numbers as encouragement",
    body: "High CTR, low retention isn’t “you’re failing.” It’s “people are clicking — the hard part’s done. They slip at 0:40; want two ways to hold them?” Every weakness → a next unlock.",
    note: "never a stats casino",
  },
  {
    tag: "04 · research",
    dot: "🌾",
    title: "The doomscroll, done for you",
    body: "A velocity radar, your true competitors measured against their own baseline, and what Reddit & niche news are buzzing about — all crossed against your fingerprint, ranked by fit.",
    note: "create more · consume less",
  },
  {
    tag: "05 · compound",
    dot: "🌸",
    title: "A memory that compounds",
    body: "One tap — nailed it / you’re wrong — and it sharpens by your next message. Warm nudges when a planted idea is ready to film or your own upload beats baseline — never competitor anxiety.",
    note: "the Sprout effect",
  },
];

const WINDOWS: [number, number][] = [
  [0.0, 0.2],
  [0.2, 0.4],
  [0.4, 0.6],
  [0.6, 0.8],
  [0.8, 1.0],
];

const TEXT_GLOW = "0 0 28px rgba(246,238,221,0.98), 0 1px 3px rgba(58,63,44,0.15)";

function FeatureBeat({ p, index }: { p: MotionValue<number>; index: number }) {
  const [a, b] = WINDOWS[index];
  const mid = (a + b) / 2;
  const opacity = useTransform(p, [a + 0.005, a + 0.045, b - 0.045, b - 0.005], [0, 1, 1, 0], { clamp: true });
  const y = useTransform(p, [a, mid], [14, 0], { clamp: true });
  const beat = BEATS[index];
  return (
    <motion.div className="absolute inset-0 flex flex-col justify-center" style={{ opacity, y }}>
      <p className="mono text-[11px] uppercase tracking-[0.16em] text-[color:var(--moss-deep)]" style={{ textShadow: TEXT_GLOW }}>
        {beat.tag}
      </p>
      <h3 className="display mt-3 text-[1.75rem] leading-[1.06] text-[color:var(--ink)] sm:text-[2.1rem] lg:text-[2.35rem]" style={{ textShadow: TEXT_GLOW }}>
        {beat.title}
      </h3>
      <p className="mt-3 max-w-md text-[14px] leading-relaxed text-[color:var(--ink-soft)] sm:text-[15px]" style={{ textShadow: TEXT_GLOW }}>
        {beat.body}
      </p>
      <span className="mt-4 w-fit rounded-full border border-[color:var(--line)] bg-white/65 px-3 py-1.5 text-[11px] text-[color:var(--ink-soft)] backdrop-blur-[2px]">
        <span className="text-[color:var(--moss-deep)]">{beat.dot}</span> {beat.note}
      </span>
    </motion.div>
  );
}

export default function GrowthStory() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const p = useSpring(scrollYProgress, { stiffness: 90, damping: 26, restDelta: 0.0005 });

  const [stage, setStage] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    setStage(Math.max(0, Math.min(BEATS.length - 1, Math.floor(v * BEATS.length))));
  });

  return (
    <section ref={ref} className="relative mt-16 h-[480vh] w-full sm:mt-24">
      <div className="sticky top-0 h-[100svh] w-full overflow-hidden">
        {/* edge-to-edge painted background */}
        <GardenPlant mode="scroll" variant="background" progress={p} className="absolute inset-0 h-full w-full" />

        {/* copy sits in the upper sky — stays clear of the soil band */}
        <div className="absolute inset-0 z-10 flex items-start pt-[8vh] sm:pt-[10vh] lg:pt-[11vh]">
          <div className="w-full max-w-xl px-6 sm:max-w-lg sm:px-10 lg:max-w-xl lg:px-14 xl:px-16">
            <p className="label" style={{ textShadow: TEXT_GLOW }}>
              water it · watch it grow
            </p>
            <div className="relative mt-4 h-[min(34vh,280px)] min-h-[200px] sm:h-[240px] lg:h-[260px]">
              {BEATS.map((_, i) => (
                <FeatureBeat key={i} p={p} index={i} />
              ))}
            </div>
          </div>
        </div>

        <div className="absolute right-5 top-1/2 z-20 hidden -translate-y-1/2 flex-col gap-3 lg:flex">
          {BEATS.map((_, i) => (
            <span
              key={i}
              className="h-2.5 w-2.5 rounded-full transition-all duration-300"
              style={{
                background: i === stage ? "var(--moss)" : "rgba(74,62,34,0.22)",
                transform: i === stage ? "scale(1.35)" : "scale(1)",
              }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

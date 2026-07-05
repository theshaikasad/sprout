"use client";

import Link from "next/link";
import { motion } from "motion/react";
import type { Variants } from "motion/react";
import GrowthStory from "@/components/GrowthStory";
import HowItWorks from "@/components/HowItWorks";
import CoreLoop from "@/components/CoreLoop";

/* ── shared "grow up" scroll reveal ─────────────────────────────────────── */
const grow: Variants = {
  hidden: { opacity: 0, y: 30, scale: 0.985 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.65, ease: [0.16, 0.8, 0.3, 1] },
  },
};
const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};
function Reveal({
  children,
  className = "",
  variants = grow,
}: {
  children: React.ReactNode;
  className?: string;
  variants?: Variants;
}) {
  return (
    <motion.div
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-70px" }}
    >
      {children}
    </motion.div>
  );
}

/* ── tiny gouache glyphs ─────────────────────────────────────────────────── */
function G({ children }: { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6">
      {children}
    </svg>
  );
}
const Icon = {
  seed: (
    <G>
      <ellipse cx="12" cy="14" rx="6" ry="7" fill="#a9743f" />
      <path d="M12 5v8" stroke="#7a4f28" strokeWidth="1.4" />
      <circle cx="12" cy="5" r="2" fill="#5d8a45" />
    </G>
  ),
  sprout: (
    <G>
      <path d="M12 21v-8" stroke="#5d8a45" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M12 13C8 13 6 10 6 7c3 0 6 2 6 5Z" fill="#7fb06a" />
      <path d="M12 12c0-3 2-5 5-5 0 3-2 5-5 5Z" fill="#5d8a45" />
    </G>
  ),
  tree: (
    <G>
      <path d="M12 22v-6" stroke="#7a4f28" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="9" r="7" fill="#5d8a45" />
      <circle cx="9" cy="8" r="1.3" fill="#e6b54b" />
      <circle cx="14" cy="11" r="1.3" fill="#e08aa0" />
    </G>
  ),
  memory: (
    <G>
      <circle cx="7" cy="8" r="2.4" fill="#5d8a45" />
      <circle cx="17" cy="7" r="2.4" fill="#cf7c4c" />
      <circle cx="12" cy="17" r="2.4" fill="#7fb0c9" />
      <path d="M9 9l6-1M8.5 10l3.5 5M16 9l-3.5 6" stroke="#8a9c7f" strokeWidth="1.1" />
    </G>
  ),
  find: (
    <G>
      <circle cx="10.5" cy="10.5" r="6" stroke="#5d8a45" strokeWidth="1.8" />
      <path d="M15 15l5 5" stroke="#3f6a32" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="10.5" cy="10.5" r="2" fill="#e6b54b" />
    </G>
  ),
  tend: (
    <G>
      <path d="M4 11h9v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3Z" fill="#7fb0c9" />
      <path d="M13 12h3l3-3" stroke="#5d8a45" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M4 11c0-1.5 1-2.5 2.5-2.5" stroke="#3f6a32" strokeWidth="1.4" />
    </G>
  ),
  compost: (
    <G>
      <path d="M6 9h12l-1.2 9a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8L6 9Z" fill="#a9743f" />
      <path d="M9 5h6l1 2H8l1-2Z" fill="#7a4f28" />
      <path d="M10 12v4M14 12v4" stroke="#f6eedd" strokeWidth="1.2" />
    </G>
  ),
  eye: (
    <G>
      <path d="M2 12c3-5 7-6 10-6s7 1 10 6c-3 5-7 6-10 6s-7-1-10-6Z" fill="#7fb0c9" opacity="0.4" />
      <circle cx="12" cy="12" r="3.4" fill="#5d8a45" />
    </G>
  ),
  spark: (
    <G>
      <path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6L12 3Z" fill="#e6b54b" />
    </G>
  ),
  quote: (
    <G>
      <rect x="3" y="6" width="18" height="12" rx="3" fill="#cf7c4c" opacity="0.85" />
      <path d="M7 10h6M7 13h9" stroke="#f6eedd" strokeWidth="1.4" strokeLinecap="round" />
    </G>
  ),
};

function YouTubeGlyph({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <path
        fill="#ff0033"
        d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8Z"
      />
      <path fill="#fff" d="M9.6 15.6 15.8 12 9.6 8.4Z" />
    </svg>
  );
}

function Logo() {
  return (
    <span className="flex items-center gap-2 text-[19px] font-semibold tracking-tight">
      <span className="grid h-8 w-8 place-items-center rounded-full bg-[color:var(--moss-a15)]">
        {Icon.sprout}
      </span>
      <span className="ital text-[color:var(--ink)]">Sprout</span>
    </span>
  );
}

/* ── content ─────────────────────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: Icon.eye,
    title: "It tells you your genre",
    body: "No niche dropdown. Your last 40 videos, weighted by what actually converts, become a fingerprint — and Sprout names it back to you before you type a word.",
  },
  {
    icon: Icon.quote,
    title: "Receipts, not vibes",
    body: "“Number-in-title: 2.1× CTR across your 5 tutorials.” Patterns are computed in Python from your analytics, kept with sample size, cited on every card. The LLM never invents a number.",
  },
  {
    icon: Icon.spark,
    title: "Every weakness → a next unlock",
    body: "High CTR, low retention doesn’t read “you’re failing.” It reads “your packaging lands — they slip at 0:40. Want two ways to hold them?” That reframe is the whole interface.",
  },
  {
    icon: Icon.find,
    title: "The doomscroll, done for you",
    body: "A velocity radar over your true niche, competitors measured against their own baselines (0.3×–10× your size), HN & Reddit crossed with your fingerprint. Distilled signal comes to you.",
  },
  {
    icon: Icon.memory,
    title: "One-tap teaching",
    body: "“Nailed it” or “you’re wrong” reweights the exact hook, format and topic behind that card. Stale trends decay out on their own; unplanted seeds compost after a few weeks.",
  },
  {
    icon: Icon.tend,
    title: "Two surfaces, one brain",
    body: "Telegram for warm nudges — celebration, idea-completion, consistency — inside an interruption budget you set. The dashboard is the garden where ideas get planted. Same memory underneath.",
  },
];

const OPS = [
  { icon: Icon.memory, k: "remember", t: "Plant the memory", b: "Your channel, analytics, competitors and live trends become one graph — scoped, typed, cited." },
  { icon: Icon.find, k: "recall", t: "Find the right seed", b: "A hand-orchestrated traversal — not one search call — joins your patterns to today’s niche." },
  { icon: Icon.tend, k: "improve", t: "Tend what works", b: "Feedback and posted videos reweight the hooks and formats that earned their place." },
  { icon: Icon.compost, k: "forget", t: "Compost what’s dead", b: "Stale trends decay out on their own. Acting on last month’s hype is worse than acting on none." },
];

export default function Landing() {
  return (
    <div className="sprout">
      <div className="sprout-sky" />
      <div className="sprout-grain" />

      <div className="relative z-10 mx-auto max-w-6xl px-5 sm:px-6">
        {/* nav */}
        <header className="flex items-center justify-between py-6">
          <Logo />
          <nav className="flex items-center gap-5 text-[14px] text-[color:var(--ink-soft)]">
            <a href="#loop" className="hidden transition-colors hover:text-[color:var(--ink)] sm:inline">
              The loop
            </a>
            <a href="#how" className="hidden transition-colors hover:text-[color:var(--ink)] sm:inline">
              How it grows
            </a>
            <a
              href="https://github.com/topoteretes/cognee"
              target="_blank"
              rel="noreferrer"
              className="hidden transition-colors hover:text-[color:var(--ink)] md:inline"
            >
              Built on Cognee
            </a>
            <Link href="/studio" className="hidden transition-colors hover:text-[color:var(--ink)] sm:inline">
              Live demo
            </Link>
            <Link href="/signup" className="btn-yt px-4 py-2 text-[13px]">
              <YouTubeGlyph className="h-4 w-4" /> Connect
            </Link>
          </nav>
        </header>

        {/* hero */}
        <section className="mt-8 max-w-3xl lg:mt-14">
          <div>
            <motion.p
              className="label flex items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--moss)]" />
              a quiet companion with a memory of you
            </motion.p>
            <motion.h1
              className="display mt-5 text-[2.7rem] leading-[1.02] sm:text-6xl"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.16, 0.8, 0.3, 1] }}
            >
              A memory of you that gets{" "}
              <span className="ital text-[color:var(--moss-deep)]">sharper</span>,
              not just bigger.
            </motion.h1>
            <motion.p
              className="mt-6 max-w-xl text-[17px] leading-relaxed text-[color:var(--ink-soft)]"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.6 }}
            >
              Sign in with YouTube once. Sprout reads the analytics only you can
              see — retention, CTR, traffic — and distills them into one memory
              of what converts <em className="ital">for you</em>. Ideas arrive as
              cards with receipts, not vibes; one tap of feedback and the next
              suggestion is sharper. Create more, consume less.
            </motion.p>
            <motion.div
              className="mt-8 flex flex-wrap items-center gap-3"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28, duration: 0.5 }}
            >
              <Link href="/signup" className="btn-yt px-6 py-3.5 text-[15px]">
                <YouTubeGlyph /> Connect with YouTube
              </Link>
              <Link href="/studio" className="btn-quiet px-5 py-3.5 text-[15px]">
                🌱 See the live demo →
              </Link>
            </motion.div>
            <motion.p
              className="mono mt-3 text-[11px] text-[color:var(--ink-faint)]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.35 }}
            >
              the demo is the real system — running on a real creator&apos;s channel, no sign-in needed
            </motion.p>
            <motion.p
              className="mono mt-6 text-[12px] text-[color:var(--ink-faint)]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              read-only OAuth · numbers computed, never estimated · every claim cited · self-hosted Cognee
            </motion.p>
          </div>
        </section>
      </div>

      {/* full-bleed scroll story — must sit outside the max-width column */}
      <div id="how" className="relative z-10">
        <GrowthStory />
      </div>

      <div className="relative z-10 mx-auto max-w-6xl px-5 pb-24 sm:px-6">
        <section id="loop" className="mt-28 sm:mt-36">
          <Reveal className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="label">the core loop · this is the whole product</p>
              <h2 className="display mt-3 max-w-xl text-3xl sm:text-4xl">
                One loop that <span className="ital text-[color:var(--moss-deep)]">compounds.</span>
              </h2>
              <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-[color:var(--ink-soft)]">
                Your analytics drip in nightly. <span className="mono text-[13px]">recall()</span>{" "}
                joins what converts for you with the live niche. Out comes a card
                with receipts — you tap once,{" "}
                <span className="mono text-[13px]">improve()</span> reweights,{" "}
                <span className="mono text-[13px]">forget()</span> composts what
                died. Watch the weights climb, lap after lap.
              </p>
            </div>
            <span className="chip">↺ running now · one lap ≈ 11s</span>
          </Reveal>
          <Reveal>
            <CoreLoop />
          </Reveal>
        </section>

        {/* features */}
        <section className="mt-28 sm:mt-36">
          <Reveal>
            <p className="label">what it does for you</p>
            <h2 className="display mt-3 max-w-2xl text-3xl sm:text-4xl">
              Everything ChatGPT can’t do{" "}
              <span className="ital text-[color:var(--moss-deep)]">because it’s never met you.</span>
            </h2>
            <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[color:var(--ink-soft)]">
              ChatGPT is a brilliant stranger every session. Sprout arms the same
              frontier brain with your private numbers, a live niche graph, and a
              memory that compounds — it wins every prompt containing{" "}
              <em className="ital">“my.”</em>
            </p>
          </Reveal>
          <Reveal variants={stagger} className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <motion.div key={f.title} variants={grow} className="card p-6">
                <span className="grid h-12 w-12 place-items-center rounded-xl bg-[color:var(--card-2)]">
                  {f.icon}
                </span>
                <p className="mt-4 text-[16px] font-semibold text-[color:var(--ink)]">{f.title}</p>
                <p className="mt-2 text-[14px] leading-relaxed text-[color:var(--ink-soft)]">{f.body}</p>
              </motion.div>
            ))}
          </Reveal>
        </section>

        {/* the four cognee ops as garden ops */}
        <section className="mt-28 sm:mt-36">
          <Reveal>
            <p className="label">the four operations underneath</p>
            <h2 className="display mt-3 max-w-2xl text-3xl sm:text-4xl">
              A gardener’s four moves —{" "}
              <span className="ital text-[color:var(--moss-deep)]">one loop that compounds.</span>
            </h2>
            <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[color:var(--ink-soft)]">
              Built directly on Cognee’s four memory ops. Nothing is generic —
              every move makes the join between your numbers, the niche, and your
              history a little sharper.
            </p>
          </Reveal>
          <Reveal variants={stagger} className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {OPS.map((o, i) => (
              <motion.div key={o.k} variants={grow} className="card relative overflow-hidden p-6">
                <span className="mono absolute right-4 top-4 text-[11px] text-[color:var(--ink-faint)]">
                  0{i + 1}
                </span>
                <span className="grid h-12 w-12 place-items-center rounded-xl bg-[color:var(--card-2)]">
                  {o.icon}
                </span>
                <p className="mono mt-4 text-[12px] uppercase tracking-widest text-[color:var(--moss-deep)]">
                  {o.k}
                </p>
                <p className="mt-1 text-[16px] font-semibold text-[color:var(--ink)]">{o.t}</p>
                <p className="mt-2 text-[14px] leading-relaxed text-[color:var(--ink-soft)]">{o.b}</p>
              </motion.div>
            ))}
          </Reveal>
        </section>

        {/* the whole flow, explained with real logos */}
        <HowItWorks />

        {/* closing CTA — the bloom */}
        <section className="mt-28 text-center sm:mt-40">
          <Reveal>
            <motion.div
              className="mx-auto mb-6 w-fit"
              initial={{ scale: 0, rotate: -30 }}
              whileInView={{ scale: 1, rotate: 0 }}
              viewport={{ once: true }}
              transition={{ type: "spring", stiffness: 130, damping: 12 }}
            >
              <svg width="56" height="56" viewBox="0 0 42 42" className="float">
                {[0, 60, 120, 180, 240, 300].map((a) => (
                  <ellipse key={a} cx="21" cy="12" rx="6" ry="9" fill="#e08aa0" transform={`rotate(${a} 21 21)`} />
                ))}
                <circle cx="21" cy="21" r="6" fill="#e6b54b" />
              </svg>
            </motion.div>
            <h2 className="display mx-auto max-w-2xl text-4xl leading-[1.05] sm:text-5xl">
              Plant your first seed{" "}
              <span className="ital text-[color:var(--moss-deep)]">today.</span>
            </h2>
            <p className="mx-auto mt-5 max-w-md text-[16px] leading-relaxed text-[color:var(--ink-soft)]">
              Create more, consume less. Let something quietly grow while you get
              back to making.
            </p>
            <div className="mt-8 flex justify-center">
              <Link href="/signup" className="btn-yt px-7 py-4 text-[16px]">
                <YouTubeGlyph className="h-5 w-5" /> Connect with YouTube
              </Link>
            </div>
          </Reveal>
        </section>

        <footer className="mt-28 flex flex-col items-center justify-between gap-3 border-t border-[color:var(--line)] pt-6 text-[12px] text-[color:var(--ink-faint)] sm:flex-row">
          <span className="flex items-center gap-2">
            <span className="grid h-5 w-5 place-items-center rounded-full bg-[color:var(--moss-a15)]">
              {Icon.sprout}
            </span>
            Sprout — WeMakeDevs × Cognee hackathon, 2026
          </span>
          <span className="mono">your data stays yours</span>
        </footer>
      </div>
    </div>
  );
}

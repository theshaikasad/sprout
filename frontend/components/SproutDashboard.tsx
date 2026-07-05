"use client";

/* eslint-disable @next/next/no-img-element */
import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "motion/react";
import { BASE, type Garden } from "@/lib/api";

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 18, scale: 0.98 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.55, ease: [0.16, 0.8, 0.3, 1] as const },
  },
};

const GRADIENTS = ["art-dawn", "art-meadow", "art-dusk", "art-forest"];

type Props = {
  garden: Garden | null;
  creatorName?: string;
  onPlant?: (id: string) => void;
};

export default function SproutDashboard({ garden, creatorName = "your", onPlant }: Props) {
  const [showNudge, setShowNudge] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-120px" });
  useEffect(() => {
    if (!inView) return;
    const t = setTimeout(() => setShowNudge(true), 1400);
    return () => clearTimeout(t);
  }, [inView]);

  const planted = garden?.planted ?? [];
  const seeds = garden?.seeds ?? [];
  const momentum = garden?.consistency?.momentum_weeks ?? 0;
  const encouragement = garden?.consistency?.encouragement ?? "Your garden is waiting — got a seed?";

  return (
    <div ref={ref} className="panel relative overflow-hidden p-3 sm:p-5">
      <div className="flex items-center justify-between gap-3 border-b border-line pb-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-accent-soft">
            <Leaf className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <p className="serif-accent text-[15px]">{creatorName}&apos;s garden</p>
            <p className="label !text-[10px] text-faint">
              {garden?.genre?.dominant_format?.replace("-", " ") ?? "tending"} · calm · nothing on fire
            </p>
          </div>
        </div>
        <span className="chip hidden sm:inline-flex">🌤 good light today</span>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate={inView ? "show" : "hidden"}
        className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]"
      >
        <div className="space-y-4">
          <motion.div variants={item} className="rounded-2xl border border-accent/25 bg-accent-soft/30 p-4">
            <p className="label !text-accent">brought to you</p>
            <p className="mt-1.5 text-[15px] leading-snug text-fg">{encouragement}</p>
          </motion.div>

          <motion.div variants={item}>
            <div className="mb-2 flex items-center justify-between">
              <p className="label">planted · your vision board</p>
              <span className="label !text-[10px] text-faint">{planted.length} growing</span>
            </div>
            {planted.length === 0 ? (
              <p className="text-sm text-dim">Nothing planted yet — got a seed?</p>
            ) : (
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {planted.map((p, i) => (
                  <div key={p.id} className="group overflow-hidden rounded-xl border border-line bg-raised">
                    <div
                      className={`art relative aspect-[16/10] w-full ${GRADIENTS[i % GRADIENTS.length]}`}
                      style={
                        p.concept_art_path?.startsWith("linear")
                          ? { background: p.concept_art_path }
                          : undefined
                      }
                    >
                      {p.concept_art_path?.startsWith("/concept-art/") && (
                        <img
                          src={`${BASE}${p.concept_art_path}`}
                          alt=""
                          className="absolute inset-0 h-full w-full object-cover"
                        />
                      )}
                      <span className="absolute left-1.5 top-1.5 z-[2] inline-flex items-center gap-1 rounded-full bg-black/25 px-1.5 py-0.5 text-[9px] font-medium text-[#f6eedd] backdrop-blur-sm">
                        <Leaf className="h-2.5 w-2.5" /> planted
                      </span>
                    </div>
                    <div className="p-2">
                      <p className="text-[11.5px] font-medium leading-tight text-fg">{p.title}</p>
                      {p.angle && <p className="mt-1 text-[10px] text-dim">{p.angle}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>

        <div className="space-y-4">
          <motion.div variants={item} className="rounded-2xl border border-line bg-raised p-4">
            <p className="label">how it&apos;s growing</p>
            <div className="mt-3 flex items-end gap-1.5" style={{ height: 46 }}>
              {[8, 12, 10, 16, 14 + momentum, 18, 22].map((h, i) => (
                <motion.span
                  key={i}
                  className="flex-1 rounded-full bg-gradient-to-t from-accent to-accent-soft"
                  initial={{ height: 4, opacity: 0.4 }}
                  animate={inView ? { height: h + 8, opacity: 1 } : {}}
                  transition={{ delay: 0.5 + i * 0.07, type: "spring", stiffness: 120, damping: 14 }}
                />
              ))}
            </div>
            <p className="mt-3 text-[13px] leading-snug text-dim">
              <span className="font-semibold text-fg">{momentum || "—"} weeks</span> of gentle momentum —
              the garden&apos;s filling in. No pressure to post; it&apos;ll wait.
            </p>
          </motion.div>

          <motion.div variants={item} className="rounded-2xl border border-dashed border-line p-4">
            <div className="flex items-center justify-between">
              <p className="label">seed tray</p>
              <span className="label !text-[10px] text-faint">{seeds.length} this week</span>
            </div>
            <p className="mt-1.5 text-[11px] text-faint">
              things you mentioned — kept, not clutter. Plant one when it feels right.
            </p>
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {seeds.length === 0 ? (
                <span className="text-[11px] text-dim">quiet tray — mention an idea in chat</span>
              ) : (
                seeds.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => onPlant?.(s.id)}
                    className="chip !py-1 text-[10px] hover:border-accent"
                  >
                    🌱 {s.title.slice(0, 40)}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        </div>
      </motion.div>

      <motion.div
        className="pointer-events-none absolute bottom-4 right-4 z-[3] max-w-[16rem]"
        initial={{ opacity: 0, y: 20, scale: 0.94 }}
        animate={showNudge ? { opacity: 1, y: 0, scale: 1 } : {}}
        transition={{ type: "spring", stiffness: 140, damping: 16 }}
      >
        <div className="rounded-2xl rounded-br-md border border-line bg-raised/95 p-3 shadow-lg backdrop-blur">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-accent-soft">
              <Leaf className="h-3 w-3" />
            </span>
            <span className="label !text-[9px] text-faint">sprout · nudge</span>
          </div>
          <p className="mt-2 text-[12px] leading-snug text-fg">{encouragement.slice(0, 120)}</p>
        </div>
      </motion.div>
    </div>
  );
}

function Leaf({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M20 4C10 4 4 10 4 20c10 0 16-6 16-16Z" fill="#47702f" />
      <path d="M17 7C13 11 9 15 6 18" stroke="#f6eedd" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

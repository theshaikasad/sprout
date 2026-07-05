"use client";

import type { Trend } from "@/lib/api";
import Thumb from "./Thumb";

/* Outliers as ride-or-pass decisions — always-visible actions, fit score from graph bridge. */

type OutlierVideo = {
  video_id: string;
  title: string;
  channel: string | null;
  views: number;
  published: string;
  trend: string;
  fit?: "strong" | "stretch" | "skip";
};

const ageDays = (iso: string) =>
  Math.max(Math.round((Date.now() - new Date(iso).getTime()) / 86400000), 0);

const FIT_LABEL = {
  strong: { text: "strong fit", cls: "text-accent" },
  stretch: { text: "stretch", cls: "text-amber" },
  skip: { text: "skip", cls: "text-faint" },
} as const;

export default function OutlierStrip({
  trends,
  activeTrend,
  onPick,
  onForget,
}: {
  trends: Trend[];
  activeTrend: string | null;
  onPick: (trendLabel: string) => void;
  onForget: (trendLabel: string) => void;
}) {
  const seen = new Set<string>();
  const outliers: OutlierVideo[] = trends
    .flatMap((t) =>
      t.evidence_videos
        .filter((v) => v.fit && v.fit !== "skip")
        .map((v) => ({ ...v, trend: t.label })),
    )
    .filter((v) => !seen.has(v.video_id) && seen.add(v.video_id))
    .sort((a, b) => b.views - a.views)
    .slice(0, 12);

  if (!outliers.length) {
    return (
      <section className="panel p-4">
        <p className="label">outliers in your niche</p>
        <p className="mt-2 text-sm text-faint">
          No semantically relevant waves right now — keyword hits were filtered out.
          Try another trend or refresh after ingest.
        </p>
      </section>
    );
  }

  return (
    <section id="outliers">
      <div className="flex items-baseline justify-between">
        <span className="label">outliers → watch it, ride or pass</span>
        <span className="font-mono text-[10px] text-faint">fit = bridge to your topics</span>
      </div>
      <div className="mt-2.5 flex gap-3 overflow-x-auto pb-2">
        {outliers.map((v) => {
          const active = activeTrend === v.trend;
          const fit = v.fit ? FIT_LABEL[v.fit] : FIT_LABEL.stretch;
          return (
            <div
              key={v.video_id}
              className={`relative shrink-0 rounded-lg border p-1.5 transition-all ${
                active
                  ? "border-accent bg-accent-soft"
                  : "border-line hover:-translate-y-0.5 hover:border-accent/50"
              }`}
            >
              <span
                className={`absolute left-2 top-2 z-10 rounded bg-raised/90 px-1.5 py-0.5 font-mono text-[8px] uppercase ${fit.cls}`}
              >
                {fit.text}
              </span>
              <Thumb
                videoId={v.video_id}
                title={`${v.title} — watch on YouTube`}
                views={v.views}
                channel={v.channel}
                w={148}
              />
              <div className="mt-1.5 flex gap-1">
                <button
                  onClick={() => onPick(v.trend)}
                  title={`suggest on "${v.trend}"`}
                  className={`flex-1 rounded-md py-1 font-mono text-[9px] transition-colors ${
                    active
                      ? "bg-accent text-[#f7fbef]"
                      : "bg-raised-2 text-dim hover:text-accent"
                  }`}
                >
                  {active ? "▸ riding" : "ride"}
                </button>
                <button
                  onClick={() => onForget(v.trend)}
                  title={`pass on "${v.trend}"`}
                  className="rounded-md border border-line bg-raised px-2 py-1 font-mono text-[9px] text-dim hover:border-amber hover:text-amber"
                >
                  pass
                </button>
              </div>
              <p className="mt-1 truncate font-mono text-[8px] text-faint">
                {v.trend} · {ageDays(v.published)}d
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

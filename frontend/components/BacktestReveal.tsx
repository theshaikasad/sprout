"use client";

import { useState } from "react";
import type { BacktestResponse } from "@/lib/api";
import Thumb, { fmtViews } from "./Thumb";

export default function BacktestReveal({
  data,
  onClose,
}: {
  data: BacktestResponse;
  onClose: () => void;
}) {
  const [revealed, setRevealed] = useState(false);
  const best = data.best_match;
  const champion = data.champion;

  return (
    <section className="rise panel relative p-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="label text-blue">temporal holdout · backtest</p>
          <h2 className="mt-2 text-2xl font-semibold leading-snug tracking-tight">
            The graph is blind to everything after{" "}
            <span className="serif-accent text-accent">{data.holdout_cutoff}</span>
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-dim">
            Every video published after this date was sealed at ingest — it never
            entered memory. We asked the blind graph about{" "}
            <span className="text-fg/90">{data.proof_trend}</span>, then broke
            the seal on what actually happened. Nothing simulated.
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-faint hover:text-fg">
          ✕
        </button>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <div>
          <h3 className="label">suggested from pre-cutoff memory only</h3>
          <ul className="mt-2 space-y-2">
            {data.suggested.cards.map((c, i) => (
              <li
                key={i}
                className={`rounded-lg border p-3.5 ${
                  best?.card_index === i
                    ? "border-accent/50 bg-accent-soft"
                    : "border-line bg-raised-2"
                }`}
              >
                <span className="font-mono text-[10px] text-faint">
                  {String(i + 1).padStart(2, "0")}
                  {best?.card_index === i && (
                    <span className="ml-2 text-accent">· best alignment</span>
                  )}
                </span>
                <p className="mt-0.5 font-medium leading-snug">{c.title}</p>
                <p className="mt-1 font-mono text-[10px] text-topic">
                  {c.topic_labels_used.join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative">
          <h3 className="label">what the creator actually posted</h3>
          <div className="relative mt-2 min-h-[16rem] overflow-hidden rounded-lg border border-line bg-raised-2">
            {!revealed && (
              <button
                onClick={() => setRevealed(true)}
                className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-[#2e3a27]/95 transition-colors hover:bg-[#2e3a27]/90"
              >
                <span
                  className="label border px-3 py-1"
                  style={{ color: "#ece5cd", borderColor: "rgba(236,229,205,0.4)" }}
                >
                  sealed · held-out data
                </span>
                <span className="serif-accent text-2xl" style={{ color: "#e6b54b" }}>
                  Break the seal ▸
                </span>
              </button>
            )}
            <div className="grid max-h-[19rem] grid-cols-3 gap-2.5 overflow-y-auto p-3">
              {data.holdout_reveal.map((v) => (
                <div
                  key={v.video_id}
                  className={
                    champion?.video_id === v.video_id
                      ? "rounded-md ring-1 ring-accent/60"
                      : ""
                  }
                >
                  <Thumb
                    videoId={v.video_id}
                    title={`${v.title} — ${v.views.toLocaleString()} views`}
                    views={v.views}
                    ratio={v.ratio_vs_baseline}
                    w={132}
                  />
                  <p className="mt-1 line-clamp-2 max-w-[132px] text-[10px] leading-tight text-dim">
                    <span
                      className={
                        v.ratio_vs_baseline >= 1.5 ? "font-semibold text-accent" : ""
                      }
                    >
                      {v.ratio_vs_baseline}×
                    </span>{" "}
                    {v.title}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {revealed && champion && (
            <div className="stamp-slam absolute -bottom-6 -right-2 max-w-[20rem] rounded-xl border border-accent bg-raised px-5 py-3 shadow-[0_8px_40px_rgba(93,138,69,0.3)]">
              <p className="label text-accent">holdout champion</p>
              <p className="serif-accent text-3xl leading-none text-accent">
                {champion.ratio_vs_baseline}× their baseline
              </p>
              <p className="mt-1.5 text-[11px] leading-snug text-dim">
                “{champion.title.slice(0, 48)}
                {champion.title.length > 48 ? "…" : ""}” — {fmtViews(champion.views)}{" "}
                real views, never in the graph
              </p>
              {best && (
                <p className="mt-2 border-t border-line pt-2 text-[11px] leading-snug text-faint">
                  Blind suggestion aligned via{" "}
                  <span className="text-dim">{best.shared_topics.join(", ")}</span>{" "}
                  → {best.ratio_vs_baseline}× on “{best.holdout_video.slice(0, 36)}…”
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

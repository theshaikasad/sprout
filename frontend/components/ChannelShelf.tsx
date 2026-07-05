"use client";

/* eslint-disable @next/next/no-img-element */

import { useState } from "react";
import type { Library } from "@/lib/api";
import Thumb, { fmtViews } from "./Thumb";

export default function ChannelShelf({ lib }: { lib: Library }) {
  const [tab, setTab] = useState<"mine" | "competitors" | "trends">("mine");

  return (
    <section className="panel">
      {/* channel banner */}
      <div className="flex items-center gap-4 border-b border-line px-5 py-4">
        {lib.creator.avatar && (
          <img
            src={lib.creator.avatar}
            alt={lib.creator.title}
            referrerPolicy="no-referrer"
            className="h-12 w-12 rounded-full border border-line"
          />
        )}
        <div className="flex-1">
          <h2 className="text-lg font-semibold leading-none tracking-tight">
            {lib.creator.title}
            <span className="ml-2 font-mono text-xs font-normal text-faint">
              {lib.creator.handle}
            </span>
          </h2>
          <p className="mt-1.5 font-mono text-[11px] text-dim">
            {fmtViews(lib.creator.subscribers)} subscribers · {lib.live_videos.length}{" "}
            videos in memory ·{" "}
            <span className="text-accent">
              {lib.holdout_count} sealed after {lib.holdout_cutoff}
            </span>
          </p>
        </div>
        <div className="flex gap-1">
          {(
            [
              ["mine", "My channel"],
              ["competitors", "Competitors"],
              ["trends", "Outliers"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                tab === key
                  ? "bg-raised-2 text-fg"
                  : "text-dim hover:text-fg"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* filmstrip */}
      <div className="flex gap-2.5 overflow-x-auto px-5 py-4">
        {tab === "mine" && (
          <>
            {lib.live_videos.map((v) => (
              <Thumb
                key={v.video_id}
                videoId={v.video_id}
                title={`${v.title} — ${v.views.toLocaleString()} views (${v.ratio}×)`}
                views={v.views}
                ratio={v.ratio}
                w={150}
              />
            ))}
            <div
              className="flex shrink-0 flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-[#ece5cd]/40 bg-[#2e3a27]/90"
              style={{ width: 150, height: (150 * 9) / 16 }}
            >
              <span className="label" style={{ fontSize: "9px", color: "#ece5cd" }}>
                sealed
              </span>
              <span className="font-mono text-xs text-[#f6eedd]/90">
                +{lib.holdout_count} videos
              </span>
              <span className="font-mono text-[8px] text-[#f6eedd]/60">
                held out for the backtest
              </span>
            </div>
          </>
        )}

        {tab === "competitors" &&
          lib.competitors.map((c) => (
            <div key={c.handle} className="shrink-0">
              <div className="mb-1.5 flex items-center gap-1.5">
                {c.avatar && (
                  <img
                    src={c.avatar}
                    alt={c.title}
                    referrerPolicy="no-referrer"
                    className="h-5 w-5 rounded-full border border-line"
                  />
                )}
                <span className="font-mono text-[10px] text-blue">
                  {c.title} · {fmtViews(c.subscribers)}
                </span>
              </div>
              <div className="flex gap-1.5">
                {c.videos.slice(0, 3).map((v) => (
                  <Thumb
                    key={v.video_id}
                    videoId={v.video_id}
                    title={`${v.title} — ${v.views.toLocaleString()} views`}
                    views={v.views}
                    w={124}
                  />
                ))}
              </div>
            </div>
          ))}

        {tab === "trends" &&
          lib.trend_videos
            .slice()
            .sort((a, b) => b.views - a.views)
            .map((v) => (
              <Thumb
                key={v.video_id}
                videoId={v.video_id}
                title={`${v.title} — ${v.channel ?? ""}`}
                views={v.views}
                channel={v.channel}
                w={150}
              />
            ))}
      </div>
    </section>
  );
}

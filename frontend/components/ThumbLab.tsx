"use client";

/* eslint-disable @next/next/no-img-element */

import { useState } from "react";
import Thumb from "./Thumb";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type ThumbReview = {
  score: number;
  verdict: string;
  works: string[];
  fix: string[];
  vs_your_winners: string;
  vs_outliers: string;
  references: {
    yours: { video_id: string; title: string; views: number }[];
    outliers: { video_id: string; title: string; views: number; channel: string }[];
  };
};

export default function ThumbLab({ ideaTitle }: { ideaTitle?: string | null }) {
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<ThumbReview | null>(null);

  async function onFile(f: File | undefined) {
    if (!f) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const dataUrl = reader.result as string;
      setPreview(dataUrl);
      setReview(null);
      setBusy(true);
      try {
        const res = await fetch(`${BASE}/thumbnail-review`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ image_data_url: dataUrl }),
        });
        setReview(await res.json());
      } finally {
        setBusy(false);
      }
    };
    reader.readAsDataURL(f);
  }

  return (
    <div className="panel p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Thumbnail lab</h2>
        <span className="label">your draft vs. what converts</span>
      </div>
      {ideaTitle && (
        <p className="mt-2 text-sm text-dim">
          For: <span className="text-fg/90">{ideaTitle}</span>
        </p>
      )}

      <div className="mt-3 flex items-start gap-4">
        <label
          className={`flex h-[72px] w-32 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-dashed text-center text-[11px] leading-snug transition-colors ${
            preview ? "border-line" : "border-line text-faint hover:border-accent/50 hover:text-dim"
          }`}
        >
          {preview ? (
            <img src={preview} alt="draft" className="h-full w-full rounded-lg object-cover" />
          ) : (
            <span>
              drop your draft
              <br />
              (click to upload)
            </span>
          )}
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
        </label>

        <div className="min-w-0 flex-1">
          {busy && (
            <p className="font-mono text-xs text-accent">
              <span className="thinking-dot">●</span> judging against your top converters +
              niche outliers…
            </p>
          )}
          {!busy && !review && (
            <p className="text-sm leading-relaxed text-faint">
              Upload a draft thumbnail. The memory compares it against your own
              top-converting thumbnails and the niche&apos;s current outliers — specific
              fixes, not generic advice.
            </p>
          )}
          {review && !busy && (
            <div className="rise">
              <div className="flex items-baseline gap-3">
                <span
                  className={`font-mono text-2xl ${
                    review.score >= 70 ? "text-accent" : review.score >= 45 ? "text-amber" : "text-dim"
                  }`}
                >
                  {review.score}
                </span>
                <span className="text-sm text-fg/90">{review.verdict}</span>
              </div>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <div>
                  <p className="label text-accent" style={{ fontSize: "9px" }}>works</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-dim">
                    {review.works?.map((w, i) => <li key={i}>· {w}</li>)}
                  </ul>
                </div>
                <div>
                  <p className="label text-amber" style={{ fontSize: "9px" }}>fix first</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-dim">
                    {review.fix?.map((f, i) => <li key={i}>· {f}</li>)}
                  </ul>
                </div>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-dim">
                <span className="text-fg/80">vs your winners:</span> {review.vs_your_winners}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-dim">
                <span className="text-fg/80">vs the niche:</span> {review.vs_outliers}
              </p>
              {review.references && (
                <div className="mt-2.5 flex gap-2 overflow-x-auto pb-1">
                  {review.references.yours.map((r) => (
                    <Thumb key={r.video_id} videoId={r.video_id} title={r.title} views={r.views} w={96} />
                  ))}
                  {review.references.outliers.map((r) => (
                    <Thumb key={r.video_id} videoId={r.video_id} title={r.title} views={r.views} channel={r.channel} w={96} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

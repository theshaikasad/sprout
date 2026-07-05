"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Review, type Trace } from "@/lib/api";
import Thumb from "./Thumb";

export default function PitchBox({
  onTrace,
  onSaved,
  seed,
}: {
  onTrace: (t: Trace | null) => void;
  onSaved: () => void;
  seed?: string | null; // e.g. a pulse item's "check the fit" — autofills and runs
}) {
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<Review | null>(null);
  const [saved, setSaved] = useState(false);

  const run = useCallback(
    async (text?: string) => {
      const pitch = (text ?? idea).trim();
      if (pitch.length < 8) return;
      setBusy(true);
      setSaved(false);
      try {
        const r = await api.review(pitch);
        setReview(r);
        onTrace(r.trace); // the graph flies through the evidence
      } finally {
        setBusy(false);
      }
    },
    [idea, onTrace],
  );

  useEffect(() => {
    if (seed) {
      setIdea(seed);
      run(seed);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed]);

  const verdictColor = (v: string) =>
    v.startsWith("make it") ? "text-accent" : v === "risky" ? "text-amber" : "text-dim";

  return (
    <div id="pitch" className="panel p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="display text-[1.35rem]">Got a seed of your own?</h2>
        <span className="label">the memory pushes back</span>
      </div>
      <div className="mt-3 flex gap-2">
        <input
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !busy && run()}
          placeholder="e.g. A video where I build an AI agent that manages my channel…"
          className="flex-1 rounded-lg border border-line bg-raised-2 px-3.5 py-2.5 text-sm outline-none placeholder:text-faint focus:border-accent/50"
        />
        <button
          onClick={() => run()}
          disabled={busy}
          className="btn-primary px-5 text-sm disabled:opacity-50"
        >
          {busy ? "Reviewing…" : "Review"}
        </button>
      </div>

      {busy && (
        <p className="mt-3 font-mono text-xs text-accent">
          <span className="thinking-dot">●</span> auditing against your memory — history,
          competitors, trends…
        </p>
      )}

      {review && !busy && (
        <div className="rise mt-4 border-t border-line pt-4">
          {review.collisions.length > 0 && (
            <div className="mb-4 rounded-lg border border-blue/40 bg-blue/5 p-3.5">
              <p className="label text-blue">collision radar</p>
              <ul className="mt-2 space-y-2">
                {review.collisions.map((c, i) => (
                  <li key={i} className="text-sm leading-snug text-fg/90">
                    {c.point}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex flex-wrap items-baseline gap-3">
            <span className={`text-xl font-semibold ${verdictColor(review.verdict)}`}>
              {review.verdict}
            </span>
            <span className="font-mono text-xs text-dim">
              confidence {review.confidence}/100
            </span>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-dim">{review.fit}</p>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            {(
              [
                ["Evidence for", review.evidence_for, "text-accent"],
                ["Evidence against", review.evidence_against, "text-amber"],
                ["Collisions", review.collisions, "text-blue"],
              ] as const
            ).map(([title, list, cls]) =>
              list.length ? (
                <div key={title} className="rounded-lg border border-line bg-raised-2 p-3">
                  <p className={`label ${cls}`}>{title}</p>
                  <ul className="mt-1.5 space-y-1.5">
                    {list.map((e, i) => (
                      <li key={i} className="text-xs leading-snug text-fg/90">
                        {e.point}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null,
            )}
          </div>

          {review.recommended && (
            <div className="mt-3 rounded-lg border border-accent/30 bg-accent-soft p-3">
              <p className="label text-accent">recommended treatment</p>
              <p className="mt-1 text-sm font-medium">{review.recommended.title}</p>
              <p className="mt-0.5 text-xs text-dim">
                <span className="font-mono">[{review.recommended.hook?.style}]</span>{" "}
                “{review.recommended.hook?.text}” · {review.recommended.format}
              </p>
            </div>
          )}

          {review.citations.length > 0 && (
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {review.citations.map((c) => (
                <Thumb
                  key={c.video_id}
                  videoId={c.video_id}
                  title={`${c.title} — ${c.views.toLocaleString()} views`}
                  views={c.views}
                  channel={c.channel}
                  w={120}
                />
              ))}
            </div>
          )}

          <button
            disabled={saved}
            onClick={async () => {
              await api.addIdea(review.recommended?.title || idea.trim(), "pitched", {
                review,
                trace: review.trace,
              });
              setSaved(true);
              onSaved();
            }}
            className="btn-ghost mt-3 px-4 py-2 text-xs font-medium disabled:opacity-50"
          >
            {saved ? "✓ Planted" : "🌱 Plant it on the board"}
          </button>
        </div>
      )}
    </div>
  );
}

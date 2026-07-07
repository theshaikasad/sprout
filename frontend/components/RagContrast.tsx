"use client";

import { useEffect, useState } from "react";
import { api, type ContrastResponse } from "@/lib/api";
import Thumb from "./Thumb";

export default function RagContrast({
  trend,
  onClose,
}: {
  trend: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<ContrastResponse | null>(null);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    api
      .contrast(trend ?? undefined)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setBusy(false));
  }, [trend]);

  const graphCard = data?.graph.headline_card;

  return (
    <section className="rise panel p-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="label text-blue">§10a · same question, two systems</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">
            Plain vector RAG vs graph join
          </h2>
          <p className="mt-1.5 max-w-xl text-sm text-dim">
            {data?.query ??
              `What should I make this week about ${trend ?? "this trend"}?`}
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-faint hover:text-fg">
          ✕
        </button>
      </div>

      {busy ? (
        <p className="mt-8 font-mono text-xs text-accent">
          <span className="thinking-dot">●</span> running both retrievers…
        </p>
      ) : data ? (
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div className="rounded-lg border border-line bg-raised-2 p-4">
            <h3 className="label text-faint">vector RAG · chunks only</h3>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-dim">
              {data.rag.answer}
            </p>
            <p className="mt-3 font-mono text-[10px] text-faint">
              {data.rag.chunks_used} transcript chunks · no trend/competitor join
            </p>
          </div>

          <div className="rounded-lg border border-accent/40 bg-accent-soft p-4">
            <h3 className="label text-accent">killer join · cited concept</h3>
            {graphCard ? (
              <>
                <p className="mt-2 text-lg font-semibold leading-snug">
                  {graphCard.title}
                </p>
                <p className="mt-1 text-sm text-dim">{graphCard.angle}</p>
                <div className="mt-2 rounded-md border-l-2 border-accent py-1 pl-2">
                  <p className="serif-accent text-sm">“{graphCard.hook.text}”</p>
                  <p className="font-mono text-[10px] text-faint">
                    {graphCard.format} · {graphCard.hook.style}
                  </p>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-dim">{graphCard.why}</p>
                <div className="mt-3 flex gap-2 overflow-x-auto">
                  {graphCard.citations.slice(0, 3).map((c) => (
                    <Thumb
                      key={c.video_id}
                      videoId={c.video_id}
                      title={c.title}
                      views={c.views}
                      channel={c.channel}
                      w={100}
                    />
                  ))}
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm text-dim">No graph card generated.</p>
            )}
          </div>

          {data.gap_finder && (
            <div className="rounded-lg border border-line bg-raised-2 p-4 md:col-span-2">
              <h3 className="label text-blue">
                gap finder · a graph anti-join vector search can&apos;t express
              </h3>
              <p className="mt-1.5 text-xs text-dim">
                Trending topics near your fingerprint with{" "}
                <span className="text-fg">no</span> video of yours covering them yet —
                a set-difference, not a similarity ranking.
              </p>
              <pre className="mt-3 overflow-x-auto rounded-md border border-line bg-raised p-3 font-mono text-[10px] leading-relaxed text-dim">
                {data.gap_finder.cypher_query}
              </pre>
              <p className="mt-2 font-mono text-[10px] text-faint">
                {data.gap_finder.raw_match_count} raw matches ·{" "}
                {data.gap_finder.gaps.length} within fingerprint distance
              </p>
              {data.gap_finder.gaps.length > 0 && (
                <ul className="mt-2 flex flex-wrap gap-2">
                  {data.gap_finder.gaps.map((gp) => (
                    <li
                      key={gp.topic_id}
                      className="rounded-full border border-accent/40 bg-accent-soft px-2.5 py-1 font-mono text-[10px] text-accent"
                    >
                      {gp.label} · d={gp.distance_to_niche}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="mt-6 text-sm text-amber">Contrast failed — is the API running?</p>
      )}
    </section>
  );
}

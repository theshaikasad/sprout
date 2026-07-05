"use client";

import { useState } from "react";
import type { Card, Trace } from "@/lib/api";
import { api } from "@/lib/api";
import { copyFilmKit } from "@/lib/filmKit";
import Thumb from "./Thumb";

function ProofStrip({
  citations,
  creatorName,
}: {
  citations: Card["citations"];
  creatorName: string | null;
}) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 flex gap-2.5 overflow-x-auto pb-1">
      {citations.map((c) => {
        const mine = creatorName && c.channel === creatorName;
        return (
          <div key={c.video_id} className="shrink-0">
            <span
              className={`label block pb-1 ${mine ? "text-accent" : "text-blue"}`}
              style={{ fontSize: "9px" }}
            >
              {mine ? "your proof" : "trending now"}
            </span>
            <Thumb
              videoId={c.video_id}
              title={`${c.title} — ${c.views.toLocaleString()} views`}
              views={c.views}
              channel={c.channel}
              w={136}
            />
          </div>
        );
      })}
    </div>
  );
}

export default function ConceptCard({
  card,
  index,
  selected,
  creatorName,
  onSelect,
  onCreate,
  created,
  readOnly = false,
  trace,
  onFeedback,
}: {
  card: Card;
  index: number;
  selected?: boolean;
  creatorName: string | null;
  onSelect?: () => void;
  onCreate?: () => void;
  created?: boolean;
  readOnly?: boolean;
  trace?: Trace;
  onFeedback?: (confirmed: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    if (await copyFilmKit(card)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <article
      onClick={readOnly ? undefined : onSelect}
      className={`rise panel p-5 transition-all duration-200 ${
        readOnly ? "" : "cursor-pointer"
      } ${
        selected
          ? "border-accent/60 shadow-[0_0_0_1px_rgba(93,138,69,0.35),0_8px_30px_rgba(93,138,69,0.12)]"
          : readOnly ? "border-line" : "hover:border-fg/25"
      }`}
      style={{ animationDelay: `${index * 120}ms` }}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="label">concept {String(index + 1).padStart(2, "0")}</span>
        <span className="rounded-md bg-raised-2 px-2 py-0.5 font-mono text-[10px] text-amber">
          {card.format}
        </span>
      </div>

      <h3 className="mt-2 text-xl font-semibold leading-snug tracking-tight">
        {card.title}
      </h3>
      {card.title_variants && card.title_variants.length > 0 && (
        <p className="mt-1 text-[11px] leading-relaxed text-faint">
          <span className="label" style={{ fontSize: "9px" }}>alt · </span>
          {card.title_variants.join("  ·  ")}
        </p>
      )}

      <ProofStrip citations={card.citations} creatorName={creatorName} />

      <p className="mt-2 text-sm leading-relaxed text-dim">{card.angle}</p>

      <div className="mt-3 rounded-lg border-l-2 border-accent bg-raised-2 py-2 pl-3 pr-2">
        <span className="label text-accent">hook · {card.hook.style}</span>
        <p className="serif-accent mt-0.5 text-base text-fg/95">“{card.hook.text}”</p>
      </div>

      <ol className="mt-3 space-y-1 text-sm text-fg/85">
        {card.outline.map((beat, i) => (
          <li key={i} className="flex gap-2.5">
            <span className="font-mono text-[10px] leading-5 text-faint">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="leading-snug">{beat}</span>
          </li>
        ))}
      </ol>

      {card.thumbnail?.concept && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-line bg-raised-2 p-2.5">
          <span
            className="flex aspect-video w-24 shrink-0 items-center justify-center overflow-hidden rounded-md px-1 text-center"
            style={{
              background:
                "radial-gradient(120% 140% at 20% 20%, rgba(230,181,75,0.55), rgba(63,106,50,0.92) 65%)",
            }}
          >
            <span className="text-[10px] font-bold uppercase leading-tight tracking-tight text-[#fdf9ee]">
              {card.thumbnail.overlay_text}
            </span>
          </span>
          <p className="text-xs leading-relaxed text-dim">
            <span className="label block" style={{ fontSize: "9px" }}>thumbnail direction</span>
            {card.thumbnail.concept}
          </p>
        </div>
      )}

      {card.broll_keywords && card.broll_keywords.length > 0 && (
        <p className="mt-2.5 text-[11px] text-faint">
          <span className="label" style={{ fontSize: "9px" }}>b-roll · </span>
          {card.broll_keywords.map((k, i) => (
            <a
              key={k}
              href={`https://www.pexels.com/search/videos/${encodeURIComponent(k)}/`}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-dim underline decoration-dotted underline-offset-2 hover:text-accent"
            >
              {k}
              {i < card.broll_keywords!.length - 1 ? ",\u00A0" : ""}
            </a>
          ))}
        </p>
      )}

      <details className="mt-3 border-t border-line pt-3">
        <summary className="cursor-pointer text-[11px] text-faint hover:text-dim">
          why this works (cited)
        </summary>
        <p className="mt-2 text-[13px] leading-relaxed text-dim">{card.why}</p>
      </details>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        {!readOnly && (
          <span
            className={`font-mono text-[10px] tracking-wider ${
              selected ? "text-accent" : "text-faint"
            }`}
          >
            {selected ? "▸ path lit in the graph" : "click to trace in graph"}
          </span>
        )}
        <div className="flex flex-wrap gap-2">
          {trace && onFeedback && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); onFeedback(true); }}
                className="rounded-lg border border-accent/40 px-2.5 py-1.5 text-[11px] text-accent"
              >
                nailed it
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onFeedback(false); }}
                className="rounded-lg border border-line px-2.5 py-1.5 text-[11px] text-dim"
              >
                you&apos;re wrong
              </button>
            </>
          )}
          <button
            onClick={handleCopy}
            className="rounded-lg border border-line px-3 py-1.5 text-[11px] font-medium text-dim transition-colors hover:border-accent/50 hover:text-accent"
          >
            {copied ? "✓ copied" : "copy film-kit"}
          </button>
          {!readOnly && onCreate && (
            <button
              disabled={created}
              onClick={(e) => {
                e.stopPropagation();
                onCreate();
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent-soft px-3.5 py-1.5 text-[11px] font-medium text-accent transition-colors hover:bg-accent hover:text-[#f7fbef] disabled:opacity-50"
            >
              <span aria-hidden>✨</span>
              {created ? "✓ on your board" : "Create"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

"use client";

import { useState } from "react";
import type { Card, Idea, Trace, Review } from "@/lib/api";
import { api } from "@/lib/api";
import ConceptCard from "./ConceptCard";

/* The plan, not just a list: every idea carries a target publish date
   (defaulted from the channel's cadence when saved). Performance feedback is
   automatic via /track — no "report a number" step anywhere. */

const STATUSES = ["saved", "scripting", "filming", "posted"] as const;

/* backend states, garden words — saved ideas are planted, posted ones sprouted */
const STATUS_LABEL: Record<string, string> = {
  seed: "🌱 seed",
  planted: "🌿 planted",
  sprouted: "🌸 sprouted",
  saved: "🌱 planted",
  scripting: "✍ scripting",
  filming: "🎬 filming",
  posted: "🌸 sprouted",
};

function dueChip(target?: string | null) {
  if (!target) return null;
  const days = Math.ceil((new Date(target).getTime() - Date.now()) / 86400000);
  if (days < 0)
    return <span className="font-mono text-[10px] text-amber">{-days}d overdue</span>;
  if (days === 0)
    return <span className="font-mono text-[10px] text-accent">film today</span>;
  return <span className="font-mono text-[10px] text-dim">in {days}d</span>;
}

function cardFromIdea(idea: Idea): Card | null {
  const p = idea.payload as { card?: Card; review?: Review; trace?: Trace };
  if (p.card) return p.card;
  const r = p.review;
  if (!r?.recommended?.title) return null;
  return {
    title: r.recommended.title,
    title_variants: [],
    angle: r.fit ?? "",
    hook: r.recommended.hook ?? { text: "", style: "question" },
    format: r.recommended.format ?? "talking-head",
    outline: [],
    why: r.fit ?? "",
    topic_labels_used: [],
    cited_video_ids: r.cited_video_ids ?? [],
    citations: r.citations ?? [],
    trace: p.trace ?? r.trace,
  } as Card;
}

export default function IdeasBoard({
  ideas,
  creatorName,
  onChanged,
  onShowGraph,
  onThumbLab,
}: {
  ideas: Idea[];
  creatorName: string | null;
  onChanged: () => void;
  onShowGraph?: (trace: Trace) => void;
  onThumbLab?: (title: string) => void;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const open = ideas.find((i) => i.id === openId);
  const openCard = open ? cardFromIdea(open) : null;

  if (!ideas.length)
    return (
      <div className="panel p-5">
        <h2 className="display text-[1.35rem]">Vision board</h2>
        <p className="mt-2 text-sm text-faint">
          Nothing planted yet — got a seed? Pick a concept from Today
          (&quot;🌱 plant it&quot;) and it takes root here with a target date from
          your posting rhythm.
        </p>
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="panel p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="display text-[1.35rem]">Vision board</h2>
          <span className="label">
            {ideas.length} growing · the garden tracks itself
          </span>
        </div>
        <ul className="mt-3 space-y-2">
          {ideas.map((it) => (
            <li
              key={it.id}
              className={`flex flex-wrap items-center gap-3 rounded-lg border px-3.5 py-2.5 transition-colors ${
                openId === it.id
                  ? "border-accent/50 bg-accent-soft"
                  : "border-line bg-raised-2"
              }`}
            >
              <span className="shrink-0 text-[13px] leading-none" aria-hidden>
                {(it.state || it.status) === "sprouted" || it.status === "posted" ? "🌸" : "🌱"}
              </span>
              <button
                type="button"
                onClick={() => setOpenId(openId === it.id ? null : it.id)}
                className="min-w-0 flex-1 truncate text-left text-sm hover:text-accent"
              >
                {it.title}
              </button>
              {dueChip(it.target)}
              <input
                type="date"
                value={it.target?.slice(0, 10) ?? ""}
                onChange={async (e) => {
                  await api.patchIdea(it.id, { target: e.target.value });
                  onChanged();
                }}
                className="rounded-md border border-line bg-raised px-1.5 py-1 font-mono text-[10px] text-dim outline-none focus:border-accent/50"
              />
              <select
                value={it.state || it.status || "planted"}
                onChange={async (e) => {
                  const v = e.target.value;
                  const stateMap: Record<string, string> = {
                    saved: "seed", scripting: "planted", filming: "planted", posted: "sprouted",
                  };
                  await api.patchIdea(it.id, { status: stateMap[v] || v });
                  onChanged();
                }}
                className="rounded-md border border-line bg-raised px-2 py-1 font-mono text-[11px] text-dim outline-none focus:border-accent/50"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </option>
                ))}
              </select>
              <button
                onClick={async () => {
                  await api.deleteIdea(it.id);
                  if (openId === it.id) setOpenId(null);
                  onChanged();
                }}
                className="text-faint transition-colors hover:text-amber"
                title="remove"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      </div>

      {open && openCard && (
        <div className="panel p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold tracking-tight">Shoot brief</h3>
            <div className="flex gap-2">
              {open.payload?.trace != null && onShowGraph && (
                <button
                  onClick={() => onShowGraph((open.payload as { trace: Trace }).trace)}
                  className="btn-ghost px-3 py-1.5 text-[11px]"
                >
                  ⛁ show in graph
                </button>
              )}
              {onThumbLab && (
                <button
                  onClick={() => onThumbLab(open.title)}
                  className="btn-ghost px-3 py-1.5 text-[11px]"
                >
                  thumb lab →
                </button>
              )}
            </div>
          </div>
          <ConceptCard
            card={openCard}
            index={0}
            creatorName={creatorName}
            readOnly
          />
        </div>
      )}
    </div>
  );
}

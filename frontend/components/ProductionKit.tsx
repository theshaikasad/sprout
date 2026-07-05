"use client";

import { useEffect, useState } from "react";
import { BASE, api, type ProductionKit as Kit } from "@/lib/api";
import Thumb from "./Thumb";

type Tab = "vision" | "production";

export default function ProductionKitPanel({
  ideaId,
  title,
  conceptArtPath,
}: {
  ideaId: string;
  title: string;
  conceptArtPath?: string;
}) {
  const [tab, setTab] = useState<Tab>("production");
  const [kit, setKit] = useState<Kit | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setErr(null);
    api
      .productionKit(ideaId)
      .then(setKit)
      .catch(() => setErr("Could not load production kit — try again after planting."))
      .finally(() => setLoading(false));
  }, [ideaId]);

  return (
    <div className="space-y-4">
      <div className="flex gap-1 rounded-lg border border-line bg-raised p-1">
        {(
          [
            ["vision", "Concept art"],
            ["production", "Production kit"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex-1 rounded-md px-3 py-1.5 text-[11px] font-medium transition-colors ${
              tab === id ? "bg-raised-2 text-accent" : "text-dim hover:text-fg"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "vision" && (
        <div className="overflow-hidden rounded-xl border border-line bg-raised">
          <div className="relative aspect-[16/10] w-full art art-meadow">
            {conceptArtPath?.startsWith("/concept-art/") && (
              <img
                src={`${BASE}${conceptArtPath}`}
                alt=""
                className="absolute inset-0 h-full w-full object-cover"
              />
            )}
            {conceptArtPath?.startsWith("linear") && (
              <div className="absolute inset-0" style={{ background: conceptArtPath }} />
            )}
          </div>
          <p className="p-3 text-[11px] leading-relaxed text-dim">
            Mood board art for the vision board — emotional direction, not a shippable thumbnail.
          </p>
        </div>
      )}

      {tab === "production" && (
        <>
          {loading && <p className="text-sm text-dim">Building your shoot kit from your patterns…</p>}
          {err && <p className="text-sm text-amber">{err}</p>}
          {kit && (
            <div className="space-y-5">
              <section className="rounded-xl border border-line bg-raised-2 p-4">
                <p className="label">Thumbnail brief · designer-executable</p>
                <p className="mt-2 font-mono text-lg font-semibold tracking-tight text-fg">
                  {kit.thumbnail_brief.overlay_text}
                </p>
                <dl className="mt-3 grid gap-2 text-[12px] text-dim sm:grid-cols-2">
                  <div>
                    <dt className="label !text-[9px]">Layout</dt>
                    <dd>{kit.thumbnail_brief.composition.layout}</dd>
                  </div>
                  <div>
                    <dt className="label !text-[9px]">Subject</dt>
                    <dd>
                      {kit.thumbnail_brief.composition.face_in_frame ? "Face" : "No face"} ·{" "}
                      {kit.thumbnail_brief.composition.subject_placement} ·{" "}
                      {kit.thumbnail_brief.composition.expression}
                    </dd>
                  </div>
                  <div>
                    <dt className="label !text-[9px]">Contrast</dt>
                    <dd>{kit.thumbnail_brief.composition.contrast_direction}</dd>
                  </div>
                  <div>
                    <dt className="label !text-[9px]">Text zone</dt>
                    <dd>{kit.thumbnail_brief.composition.text_zone}</dd>
                  </div>
                </dl>
                <p className="mt-3 text-[12px] leading-relaxed text-fg/90">
                  {kit.thumbnail_brief.designer_notes}
                </p>
                {kit.thumbnail_brief.precedents.length > 0 && (
                  <div className="mt-4">
                    <p className="label !text-[9px]">Visual precedents (your top CTR)</p>
                    <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                      {kit.thumbnail_brief.precedents.map((p) => (
                        <div key={p.video_id} className="shrink-0">
                          <Thumb videoId={p.video_id} title={p.title} w={120} />
                          <p className="mt-1 max-w-[120px] truncate font-mono text-[9px] text-faint">
                            CTR {(p.ctr * 100).toFixed(1)}%
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {kit.thumbnail_brief.receipts.length > 0 && (
                  <ul className="mt-3 space-y-1 border-t border-line pt-3 text-[10px] text-faint">
                    {kit.thumbnail_brief.receipts.map((r, i) => (
                      <li key={i}>
                        {r.pattern_label || r.note || r.type} · n={r.support_n ?? "—"} ·{" "}
                        {r.effect_size ? `${r.effect_size}×` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="rounded-xl border border-line bg-raised-2 p-4">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="label">Script skeleton · retention beats</p>
                  <span className="font-mono text-[10px] text-faint">
                    ~{kit.script_skeleton.total_target} · {kit.script_skeleton.format}
                  </span>
                </div>
                <ol className="mt-3 space-y-3">
                  {kit.script_skeleton.beats.map((beat) => (
                    <li
                      key={`${beat.type}-${beat.start_sec}`}
                      className="rounded-lg border border-line/80 bg-raised px-3 py-2.5"
                    >
                      <div className="flex flex-wrap items-baseline gap-2">
                        <span className="font-mono text-[10px] uppercase text-accent">
                          {beat.type}
                        </span>
                        <span className="font-mono text-[10px] text-faint">{beat.time_range}</span>
                        <span className="text-[10px] text-dim">({beat.target_duration_sec}s)</span>
                      </div>
                      <p className="mt-1 text-sm font-medium text-fg">{beat.line}</p>
                      <p className="mt-1 text-[12px] leading-relaxed text-dim">{beat.guidance}</p>
                      {beat.receipts.length > 0 && (
                        <ul className="mt-2 space-y-0.5 text-[10px] text-faint">
                          {beat.receipts.map((r, i) => (
                            <li key={i}>
                              ↳ {r.pattern_label || r.note} · n={r.support_n ?? "—"}
                              {r.effect_size ? ` · ${r.effect_size}×` : ""}
                            </li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          )}
        </>
      )}
    </div>
  );
}

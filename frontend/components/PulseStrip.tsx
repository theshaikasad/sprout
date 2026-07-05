"use client";

import type { Pulse } from "@/lib/api";

export default function PulseStrip({
  pulse,
  onFitCheck,
}: {
  pulse: Pulse | null;
  onFitCheck: (title: string) => void;
}) {
  if (!pulse?.items?.length) {
    return (
      <section className="panel p-4">
        <p className="label">discourse radar</p>
        <p className="mt-2 text-sm text-faint">
          Reddit + Hacker News for your corner of the internet — ranked by fit to your fingerprint.
        </p>
      </section>
    );
  }
  return (
    <section>
      <div className="flex items-baseline justify-between">
        <span className="label">discourse · your corner of the internet</span>
        <span className="font-mono text-[10px] text-faint">reddit · hacker news</span>
      </div>
      <div className="mt-2.5 flex gap-2.5 overflow-x-auto pb-2">
        {pulse.items.map((it, i) => (
          <div key={`${it.source}-${i}`} className="panel flex w-60 shrink-0 flex-col p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="max-w-[9rem] truncate rounded border border-line px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-dim">
                {it.source}
              </span>
              {it.fit != null && it.fit > 0 && (
                <span className="font-mono text-[10px] text-accent">fit {it.fit}</span>
              )}
            </div>
            <a
              href={it.url}
              target="_blank"
              rel="noreferrer"
              title={it.title}
              className="mt-2 line-clamp-2 flex-1 text-[13px] font-medium leading-snug transition-colors hover:text-accent"
            >
              {it.title}
            </a>
            <button
              onClick={() => onFitCheck(it.title)}
              className="mt-2 self-start font-mono text-[10px] text-faint transition-colors hover:text-accent"
            >
              ▸ check the fit for my channel
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

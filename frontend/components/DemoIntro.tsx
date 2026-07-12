"use client";

/** The framing strip for cold visitors: what this is, whose channel, why it's real.
    Shown whenever nobody is signed in — i.e. always, in the public demo. */
export default function DemoIntro({
  onShowGraph,
  onRunBacktest,
  busy,
}: {
  onShowGraph: () => void;
  onRunBacktest: () => void;
  busy?: boolean;
}) {
  return (
    <section className="panel border-accent/30 bg-accent-soft/20 p-5">
      <p className="label text-accent">live demo — nothing here is mocked</p>
      <h2 className="display mt-1.5 text-[1.3rem] leading-snug">
        An AI companion with a persistent memory of one YouTube creator.
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-dim">
        You&apos;re seeing the studio of <strong className="text-fg">@LanaBlakely</strong> (1.65M
        subs, slow-living essays): ~60 of her real videos, transcripts, and analytics, distilled
        into a knowledge graph this page queries live. Every suggestion below must cite her real
        videos as receipts — uncited ideas are discarded before you ever see them.
      </p>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        <button
          onClick={onShowGraph}
          className="text-xs font-medium text-accent underline decoration-dotted underline-offset-4 hover:text-fg"
        >
          show the memory graph →
        </button>
        <button
          onClick={onRunBacktest}
          disabled={busy}
          className="text-xs font-medium text-accent underline decoration-dotted underline-offset-4 hover:text-fg disabled:opacity-50"
        >
          prove it — run the backtest →
        </button>
      </div>
    </section>
  );
}

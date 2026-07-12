"use client";

import { useEffect, useState } from "react";

const KEY = "ms_toured_v2";

const STEPS = [
  {
    target: "what is this",
    title: "A live memory of one real channel",
    body: "Sprout is an AI companion that remembers a creator. This demo runs on @LanaBlakely's real channel — her videos, transcripts, and analytics, distilled into the knowledge graph on the right. Nothing is mocked.",
  },
  {
    target: "how it works",
    title: "Cited concepts, already loaded",
    body: "The cards below are new video ideas retrieved from that memory. The thumbnails under each are receipts — her video that proves the pattern, plus one proving demand. Uncited ideas get discarded.",
  },
  {
    target: "teach it",
    title: "Feedback actually changes it",
    body: "“Nailed it” or “you're wrong” on a card reweights the graph (improve()) and the next batch visibly shifts. The memory gets sharper, not just bigger.",
  },
  {
    target: "why believe it",
    title: "Proof, not vibes",
    body: "Scroll to “Why believe it”: a backtest where the memory was blinded to her last 3 months and pointed at videos she actually made — and a side-by-side against plain RAG.",
  },
];

export default function CoachMarks({ skip }: { skip?: boolean }) {
  const [step, setStep] = useState(-1);

  useEffect(() => {
    if (skip || typeof window === "undefined") return;
    if (localStorage.getItem(KEY)) return;
    setStep(0);
  }, [skip]);

  if (step < 0 || step >= STEPS.length) return null;

  const s = STEPS[step];

  function dismiss() {
    if (step >= STEPS.length - 1) {
      localStorage.setItem(KEY, "1");
      setStep(-1);
    } else {
      setStep(step + 1);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-[#3a3f2c]/40 p-4 backdrop-blur-[2px] sm:items-center">
      <div className="rise panel max-w-md p-5 shadow-2xl">
        <p className="label text-accent">
          {step + 1} / {STEPS.length} · {s.target}
        </p>
        <h3 className="mt-2 text-lg font-semibold">{s.title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-dim">{s.body}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={() => {
              localStorage.setItem(KEY, "1");
              setStep(-1);
            }}
            className="btn-ghost px-3 py-1.5 text-xs"
          >
            skip
          </button>
          <button onClick={dismiss} className="btn-primary px-4 py-1.5 text-xs">
            {step >= STEPS.length - 1 ? "got it" : "next →"}
          </button>
        </div>
      </div>
    </div>
  );
}

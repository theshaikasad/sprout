"use client";

import { useEffect, useState } from "react";

const KEY = "ms_toured";

const STEPS = [
  {
    target: "outliers",
    title: "Real outlier videos",
    body: "These are actual niche videos pulling views — watch one, then ride the wave or pass.",
  },
  {
    target: "concepts",
    title: "Cited concepts",
    body: "Every card cites your proof videos first. Click to light up the graph path behind it.",
  },
  {
    target: "board",
    title: "Plant it",
    body: "🌱 plant it tucks the full shoot brief into your vision board with a target publish date.",
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

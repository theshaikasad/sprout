"use client";

/* The board's background = the genre fingerprint made visible (spec: "the
   garden paints itself to match you"). Studio already sits on the shared
   .atmosphere wash from layout.tsx; this adds the one thing that's actually
   distinctive to Sprout — the painted GardenPlant scene, roots labeled with
   the real graph edges (hooks/formats/topics/trends/rivals), held in a
   fully-bloomed, static state (no scroll-drive, no re-animate on tab change).
   Low opacity + fixed behind z-10 content: panels are opaque cream cards on
   top, so this only ever shows in the margins — atmosphere, not decoration
   fighting for attention. */

import { useMotionValue } from "motion/react";
import { GardenPlant } from "./GardenScene";

export default function DashboardBackdrop() {
  const progress = useMotionValue(1); // always in bloom — this is the lived-in garden, not onboarding's reveal

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 opacity-[0.16] mix-blend-multiply"
    >
      <GardenPlant
        mode="scroll"
        variant="background"
        progress={progress}
        className="absolute inset-0 h-full w-full"
      />
    </div>
  );
}

/* Gouache glyphs for Sprout's four Cognee ops — shared across landing surfaces. */

function G({ children }: { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6">
      {children}
    </svg>
  );
}

export const SproutGlyph = {
  remember: (
    <G>
      <circle cx="7" cy="8" r="2.4" fill="#5d8a45" />
      <circle cx="17" cy="7" r="2.4" fill="#cf7c4c" />
      <circle cx="12" cy="17" r="2.4" fill="#7fb0c9" />
      <path d="M9 9l6-1M8.5 10l3.5 5M16 9l-3.5 6" stroke="#8a9c7f" strokeWidth="1.1" />
    </G>
  ),
  recall: (
    <G>
      <circle cx="10.5" cy="10.5" r="6" stroke="#5d8a45" strokeWidth="1.8" />
      <path d="M15 15l5 5" stroke="#3f6a32" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="10.5" cy="10.5" r="2" fill="#e6b54b" />
    </G>
  ),
  improve: (
    <G>
      <path d="M4 11h9v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3Z" fill="#7fb0c9" />
      <path d="M13 12h3l3-3" stroke="#5d8a45" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M4 11c0-1.5 1-2.5 2.5-2.5" stroke="#3f6a32" strokeWidth="1.4" />
    </G>
  ),
  forget: (
    <G>
      <path d="M6 9h12l-1.2 9a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8L6 9Z" fill="#a9743f" />
      <path d="M9 5h6l1 2H8l1-2Z" fill="#7a4f28" />
      <path d="M10 12v4M14 12v4" stroke="#f6eedd" strokeWidth="1.2" />
    </G>
  ),
};

export const LOOP_OPS = [
  { key: "remember", glyph: SproutGlyph.remember, hint: "analytics drip in nightly" },
  { key: "recall", glyph: SproutGlyph.recall, hint: "join × niche × rivals" },
  { key: "improve", glyph: SproutGlyph.improve, hint: "your one tap reweights" },
  { key: "forget", glyph: SproutGlyph.forget, hint: "compost stale trends" },
] as const;

function DashboardGlyph({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none">
      <rect x="2.5" y="4" width="19" height="16" rx="3" fill="#f0e6d0" stroke="#5d8a45" strokeWidth="1.3" />
      <rect x="5" y="7" width="6" height="5" rx="1.5" fill="#9dbf88" />
      <path d="M13.5 8h4M13.5 11h3" stroke="#5d8a45" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export { DashboardGlyph };

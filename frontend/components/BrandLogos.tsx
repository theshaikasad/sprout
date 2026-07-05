/* Simplified brand marks for the "how it works" flow + the powered-by strip.
   Hand-drawn recognizable SVGs (no external requests), each in its brand color,
   always shown with a text label so recognition never depends on pixel-accuracy. */

type P = { className?: string };
const box = (className = "h-6 w-6") => className;

export function Cognee({ className }: P) {
  // graph memory — connected nodes, Cognee's core motif
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <rect x="1" y="1" width="22" height="22" rx="6" fill="#101d18" />
      <path d="M8 8.5 15.5 9M8 8.5 12 15.5M15.5 9 12 15.5" stroke="#57c99a" strokeWidth="1.1" strokeOpacity="0.7" />
      <circle cx="8" cy="8.5" r="2.1" fill="#57c99a" />
      <circle cx="15.5" cy="9" r="1.7" fill="#8fe3c2" />
      <circle cx="12" cy="15.5" r="1.7" fill="#3f9a76" />
    </svg>
  );
}

export function YouTube({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <rect x="1" y="5" width="22" height="14" rx="4.5" fill="#FF0033" />
      <path d="M10 9.2 16 12l-6 2.8z" fill="#fff" />
    </svg>
  );
}

export function Telegram({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <defs>
        <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2AABEE" />
          <stop offset="100%" stopColor="#229ED9" />
        </linearGradient>
      </defs>
      <circle cx="12" cy="12" r="11" fill="url(#tg)" />
      <path
        d="M5.6 11.8 16.7 7.5c.6-.2 1.1.1.9.9l-1.9 8.9c-.1.6-.5.75-1 .47l-2.7-2-1.3 1.26c-.15.15-.27.27-.55.27l.2-2.85 5.15-4.66c.22-.2-.05-.31-.34-.12l-6.36 4-2.74-.86c-.6-.19-.6-.6.14-.89z"
        fill="#fff"
      />
    </svg>
  );
}

export function OpenAI({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <g stroke="#10A37F" strokeWidth="1.5" fill="none">
        <ellipse cx="12" cy="12" rx="9" ry="4" />
        <ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(60 12 12)" />
        <ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(120 12 12)" />
      </g>
      <circle cx="12" cy="12" r="2" fill="#10A37F" />
    </svg>
  );
}

export function HackerNews({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <rect x="1" y="1" width="22" height="22" rx="3.5" fill="#FF6600" />
      <path d="M12 17v-4l-3.2-6h2.1L12 10.6 13.1 7h2.1L12 13z" fill="#fff" />
    </svg>
  );
}

export function Reddit({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <circle cx="12" cy="12" r="11" fill="#FF4500" />
      <line x1="12.5" y1="12" x2="15.5" y2="5.5" stroke="#fff" strokeWidth="1.1" />
      <circle cx="15.6" cy="5.2" r="1.4" fill="#fff" />
      <ellipse cx="12" cy="14" rx="7" ry="5" fill="#fff" />
      <circle cx="9.6" cy="13.4" r="1.1" fill="#FF4500" />
      <circle cx="14.4" cy="13.4" r="1.1" fill="#FF4500" />
      <path d="M9.4 16.2c1.6 1.1 3.6 1.1 5.2 0" stroke="#FF4500" strokeWidth="0.9" strokeLinecap="round" />
    </svg>
  );
}

export function Python({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <path
        d="M11.6 2.2c-4.4 0-4.1 1.9-4.1 1.9v2h4.2v.6H5.9S3 6.4 3 11s2.5 4.4 2.5 4.4h1.5v-2.1s-.08-2.5 2.5-2.5h4.2s2.4.04 2.4-2.3V4.6S16.9 2.2 11.6 2.2ZM9.3 3.5c.42 0 .76.34.76.76s-.34.76-.76.76-.76-.34-.76-.76.34-.76.76-.76Z"
        fill="#3776AB"
      />
      <path
        d="M12.4 21.8c4.4 0 4.1-1.9 4.1-1.9v-2h-4.2v-.6h5.8S21 17.6 21 13s-2.5-4.4-2.5-4.4H17v2.1s.08 2.5-2.5 2.5h-4.2S7.9 13.2 7.9 15.5v3.9S7.1 21.8 12.4 21.8Zm2.3-1.3c-.42 0-.76-.34-.76-.76s.34-.76.76-.76.76.34.76.76-.34.76-.76.76Z"
        fill="#FFD343"
      />
    </svg>
  );
}

export function Firebase({ className }: P) {
  return (
    <svg viewBox="0 0 24 24" className={box(className)} fill="none">
      <path d="M4 18 8.5 4.5c.3-.9 1.2-.8 1.6 0L12 8.2 6.5 18z" fill="#FFC24A" />
      <path d="M4 18 6.5 8.6c.25-.9 1.05-.9 1.5-.15L18 18z" fill="#F4BD62" />
      <path d="M4 18 14.6 6.4c.5-.5 1.2-.35 1.4.4L18 18l-6.6 3.4c-.5.25-1 .25-1.5 0z" fill="#F6820C" />
      <path d="M4 18l6.4 3.4c.5.25 1 .25 1.5 0L18 18z" fill="#FDE068" opacity="0.35" />
    </svg>
  );
}

export function GoogleG({ className }: P) {
  return (
    <svg viewBox="0 0 48 48" className={box(className)} fill="none" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.2C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.2C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

/* small logo + label used across the flow and the powered-by strip */
export function LogoChip({
  logo,
  label,
  sub,
}: {
  logo: React.ReactNode;
  label: string;
  sub?: string;
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-white/55 px-3 py-1.5">
      <span className="grid h-6 w-6 shrink-0 place-items-center">{logo}</span>
      <span className="leading-tight">
        <span className="block text-[13px] font-medium text-[color:var(--ink)]">{label}</span>
        {sub && <span className="mono block text-[9px] text-[color:var(--ink-faint)]">{sub}</span>}
      </span>
    </span>
  );
}

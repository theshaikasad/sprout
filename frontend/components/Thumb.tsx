"use client";

/* eslint-disable @next/next/no-img-element -- i.ytimg.com thumbnails, no optimization needed */

export const thumbUrl = (videoId: string, q: "mq" | "hq" = "mq") =>
  `https://i.ytimg.com/vi/${videoId}/${q}default.jpg`;

export const fmtViews = (v: number) =>
  v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(1)}M`
    : v >= 1000
      ? `${(v / 1000).toFixed(v >= 10_000 ? 0 : 1)}k`
      : `${v}`;

export default function Thumb({
  videoId,
  title,
  views,
  ratio,
  channel,
  w = 160,
  href = true,
}: {
  videoId: string;
  title: string;
  views?: number;
  ratio?: number;
  channel?: string | null;
  w?: number;
  href?: boolean;
}) {
  const img = (
    <span
      className="group/thumb relative block shrink-0 overflow-hidden rounded-md border border-line bg-raised-2"
      style={{ width: w, height: (w * 9) / 16 }}
      title={title}
    >
      <img
        src={thumbUrl(videoId)}
        alt={title}
        loading="lazy"
        className="h-full w-full object-cover transition-all duration-200 [filter:saturate(0.85)] group-hover/thumb:[filter:none]"
      />
      {views !== undefined && (
        <span className="absolute bottom-0 right-0 rounded-tl bg-black/75 px-1 py-px font-mono text-[9px] text-[#f6eedd]">
          {fmtViews(views)}
        </span>
      )}
      {ratio !== undefined && ratio >= 2 && (
        <span className="absolute left-0 top-0 rounded-br bg-accent px-1 py-px font-mono text-[9px] font-semibold text-[#f7fbef]">
          {ratio}×
        </span>
      )}
      {channel && (
        <span className="absolute bottom-0 left-0 max-w-[70%] truncate rounded-tr bg-black/60 px-1 py-px font-mono text-[8px] text-[#f6eedd]/85">
          {channel}
        </span>
      )}
    </span>
  );

  return href ? (
    <a
      href={`https://youtube.com/watch?v=${videoId}`}
      target="_blank"
      rel="noreferrer"
      onClick={(e) => e.stopPropagation()}
      className="shrink-0"
    >
      {img}
    </a>
  ) : (
    img
  );
}

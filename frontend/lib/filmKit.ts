import type { Card } from "./api";

/** One-click shoot brief for Notion/Docs. */
export function filmKitMarkdown(card: Card): string {
  const lines = [
    `# ${card.title}`,
    "",
    `**Format:** ${card.format}`,
    `**Hook (${card.hook.style}):** "${card.hook.text}"`,
    "",
  ];
  if (card.title_variants?.length) {
    lines.push("## Title variants", ...card.title_variants.map((t) => `- ${t}`), "");
  }
  if (card.angle) {
    lines.push(`**Angle:** ${card.angle}`, "");
  }
  lines.push("## Outline");
  card.outline.forEach((beat, i) => lines.push(`${i + 1}. ${beat}`));
  lines.push("");
  if (card.thumbnail?.concept) {
    lines.push(
      "## Thumbnail",
      `- Visual: ${card.thumbnail.concept}`,
      `- Overlay: ${card.thumbnail.overlay_text}`,
      "",
    );
  }
  if (card.broll_keywords?.length) {
    lines.push(
      "## B-roll",
      ...card.broll_keywords.map(
        (k) => `- ${k} — https://www.pexels.com/search/videos/${encodeURIComponent(k)}/`,
      ),
      "",
    );
  }
  lines.push("## Why (cited)", card.why, "");
  if (card.citations.length) {
    lines.push("## Proof videos");
    card.citations.forEach((c) => {
      lines.push(
        `- [${c.title}](https://youtube.com/watch?v=${c.video_id}) — ${c.views.toLocaleString()} views (${c.channel ?? "?"})`,
      );
    });
  }
  return lines.join("\n");
}

export async function copyFilmKit(card: Card): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(filmKitMarkdown(card));
    return true;
  } catch {
    return false;
  }
}

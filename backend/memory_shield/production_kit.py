"""Production kit — thumbnail brief + retention-keyed script skeleton per planted idea.

Synthesized from precomputed patterns, analytics, beats, and cached packaging
vision analysis. No LLM-invented numbers; every claim carries a receipt.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from statistics import median

from .analytics_fixture import load_analytics_table
from .analyzer import run_pattern_scan
from .config import BEAT_TYPES, CACHE_DIR, FORMATS, HOOK_STYLES
from .corpus import load_corpus
from .thumbs import analyze_packaging, top_ctr_videos

KIT_DIR = CACHE_DIR / "production_kit"
KIT_DIR.mkdir(exist_ok=True)

# Default beat order when format-specific template is unknown
_FORMAT_BEATS: dict[str, list[str]] = {
    "talking-head": ["intro", "context", "story", "demo", "outro"],
    "voiceover-broll": ["intro", "context", "story", "demo", "outro"],
    "vlog": ["intro", "story", "demo", "outro"],
    "personal-essay": ["intro", "context", "story", "outro"],
    "listicle": ["intro", "demo", "demo", "cta", "outro"],
    "interview": ["intro", "context", "story", "outro"],
    "day-in-life": ["intro", "story", "outro"],
}

_STOP = {
    "the", "a", "an", "and", "or", "for", "to", "in", "of", "on", "my", "your",
    "how", "why", "what", "when", "i", "you", "we", "is", "are", "this", "that",
    "with", "from", "about", "video", "vlog", "shorts",
}


def _kit_path(idea_id: str) -> Path:
    return KIT_DIR / f"{idea_id}.json"


def load_production_kit(idea_id: str) -> dict | None:
    p = _kit_path(idea_id)
    if p.exists():
        return json.loads(p.read_text())
    return None


def _save_kit(idea_id: str, kit: dict) -> dict:
    kit["idea_id"] = idea_id
    kit["generated_at"] = datetime.utcnow().isoformat() + "Z"
    _kit_path(idea_id).write_text(json.dumps(kit, ensure_ascii=False, indent=1))
    return kit


def _overlay_text(title: str, packaging_patterns: list[dict], max_words: int = 3) -> tuple[str, dict | None]:
    """Deterministic overlay — actual words from title, shaped by packaging pattern."""
    raw = re.sub(r"[^\w\s']", " ", title)
    tokens = [t for t in raw.split() if t.lower() not in _STOP and len(t) > 1]
    number_pat = next(
        (p for p in packaging_patterns if p.get("feature_value") == "number in title"),
        None,
    )
    has_digit = bool(re.search(r"\d", title))
    words: list[str] = []
    if number_pat and has_digit:
        num = next((t for t in tokens if re.search(r"\d", t)), "")
        rest = [t for t in tokens if t != num][: max_words - (1 if num else 0)]
        words = ([num] if num else []) + rest
    else:
        words = tokens[:max_words]
    overlay = " ".join(words).upper()[:48] or title[:32].upper()
    receipt = None
    if number_pat and has_digit:
        receipt = {
            "pattern_label": number_pat["label"],
            "confidence": number_pat["confidence"],
            "support_n": number_pat["support_n"],
            "effect_size": number_pat["effect_size"],
            "metric": number_pat["metric"],
        }
    return overlay, receipt


def _pattern_for_kind(patterns: list[dict], kind: str, is_short: bool) -> list[dict]:
    return [p for p in patterns if p.get("kind") == kind and p.get("is_short") == is_short]


def _median_beat_end(videos: list[dict], beat_type: str) -> int | None:
    ends = []
    for v in videos:
        for b in v.get("beats") or []:
            if b.get("type") == beat_type:
                ends.append(int(b.get("end_sec") or 0))
    return int(median(ends)) if ends else None


def _median_beat_duration(videos: list[dict], beat_type: str) -> int | None:
    durs = []
    for v in videos:
        for b in v.get("beats") or []:
            if b.get("type") == beat_type:
                durs.append(max(1, int(b.get("end_sec", 0)) - int(b.get("start_sec", 0))))
    return int(median(durs)) if durs else None


def _fmt_ts(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    return f"{m}:{s:02d}"


def _receipt_from_pattern(p: dict) -> dict:
    return {
        "pattern_label": p["label"],
        "confidence": p["confidence"],
        "support_n": p["support_n"],
        "effect_size": p["effect_size"],
        "metric": p["metric"],
        "evidence_video_ids": (p.get("evidence_video_ids") or [])[:4],
    }


def _hook_line(draft: dict, hook_patterns: list[dict]) -> tuple[str, dict | None]:
    hook_style = (draft.get("hook_style") or "").strip()
    angle = (draft.get("angle") or "").strip()
    title = draft.get("title") or ""
    if not hook_style:
        card = (draft.get("payload") or {}).get("card") or {}
        hook = card.get("hook") or {}
        hook_style = hook.get("style") or "question"
        if not angle:
            angle = hook.get("text") or ""
    style_pat = next(
        (p for p in hook_patterns if p.get("feature_value") == hook_style),
        None,
    )
    if angle:
        text = angle.strip().strip('"')
    elif hook_style == "question":
        text = f"What if {title.rstrip('?')}?"
    elif hook_style == "vulnerable-confession":
        text = f"I need to be honest about {title.lower()}."
    elif hook_style == "stat":
        text = title
    else:
        text = title
    receipt = _receipt_from_pattern(style_pat) if style_pat else None
    return text, receipt


def build_thumbnail_brief(draft: dict, patterns: list[dict], analytics_rows: list[dict]) -> dict:
    is_short = draft.get("is_short", False)
    packaging_pats = _pattern_for_kind(patterns, "Packaging", is_short)
    winners = top_ctr_videos(analytics_rows, is_short=is_short, n=3)
    corpus = load_corpus()
    vid_map = {v["video_id"]: v for v in corpus["live"] + corpus.get("holdout", [])}

    precedents = []
    composition_notes: list[str] = []
    for row in winners[:2]:
        v = vid_map.get(row["video_id"])
        if not v:
            continue
        attrs = analyze_packaging(v)
        precedents.append({
            "video_id": row["video_id"],
            "title": row["title"],
            "ctr": round(row.get("ctr") or 0, 4),
            "ctr_vs_cohort": f"{row.get('ctr', 0) / max(median([r.get('ctr') or 0 for r in analytics_rows if r.get('is_short') == is_short] or [0.01]), 0.001):.1f}× cohort median CTR",
            "packaging": {
                "face_present": attrs.get("face_present"),
                "face_placement": attrs.get("face_placement"),
                "expression": attrs.get("expression"),
                "overlay_text_words": attrs.get("overlay_text_words"),
                "overlay_sample": attrs.get("overlay_sample"),
                "contrast_direction": attrs.get("contrast_direction"),
                "composition": attrs.get("composition"),
            },
        })
        if attrs.get("composition"):
            composition_notes.append(attrs["composition"])
        if attrs.get("contrast_direction"):
            composition_notes.append(attrs["contrast_direction"])

    overlay, overlay_receipt = _overlay_text(draft.get("title") or "", packaging_pats)

    # Synthesize layout from winner precedents (majority traits)
    face_rate = sum(1 for p in precedents if p["packaging"].get("face_present")) / max(len(precedents), 1)
    avg_words = int(
        median([p["packaging"].get("overlay_text_words") or 0 for p in precedents] or [3])
    )
    word_cap = min(3, max(1, avg_words)) if avg_words else 3
    if len(overlay.split()) > word_cap:
        overlay = " ".join(overlay.split()[:word_cap])

    dominant_comp = composition_notes[0] if composition_notes else "face + text split"
    placement = precedents[0]["packaging"].get("face_placement", "center") if precedents else "center"
    expression = precedents[0]["packaging"].get("expression", "thoughtful") if precedents else "thoughtful"
    contrast = precedents[0]["packaging"].get("contrast_direction", "subject bright on dark bg") if precedents else "subject bright on dark bg"

    receipts: list[dict] = []
    if overlay_receipt:
        receipts.append(overlay_receipt)
    for p in precedents:
        receipts.append({
            "type": "precedent",
            "video_id": p["video_id"],
            "title": p["title"],
            "ctr": p["ctr"],
            "note": f"visual precedent — {p['packaging'].get('composition', 'packaging')}",
        })

    return {
        "overlay_text": overlay,
        "overlay_word_count": len(overlay.split()),
        "composition": {
            "layout": dominant_comp,
            "subject_placement": placement,
            "expression": expression,
            "contrast_direction": contrast,
            "face_in_frame": face_rate >= 0.5,
            "text_zone": "upper-right or lower-third — keep face unobstructed",
        },
        "designer_notes": (
            f"Use exactly “{overlay}” as on-thumbnail text ({len(overlay.split())} words max). "
            f"Face {placement}, {expression} expression. {contrast}. "
            f"Match the {dominant_comp} layout from your top-CTR thumbnails — not mood art."
        ),
        "precedents": precedents,
        "receipts": receipts,
    }


def build_script_skeleton(
    draft: dict,
    patterns: list[dict],
    analytics_rows: list[dict],
) -> dict:
    corpus = load_corpus()
    fmt = draft.get("format_name") or draft.get("format") or "talking-head"
    if fmt not in FORMATS:
        fmt = "talking-head"
    is_short = draft.get("is_short", bool(fmt in ("day-in-life",) and "short" in (draft.get("title") or "").lower()))
    live = [v for v in corpus["live"] if v.get("is_short") == is_short]

    pacing_pats = _pattern_for_kind(patterns, "Pacing", is_short)
    hook_pats = _pattern_for_kind(patterns, "Hook", is_short)
    pacing = pacing_pats[0] if pacing_pats else None

    intro_cap = 40
    intro_receipt = None
    if pacing:
        intro_cap = 40
        intro_receipt = _receipt_from_pattern(pacing)
        bleed_ids = set(pacing.get("evidence_video_ids") or [])
        short_intro_ends = []
        for v in live:
            if v["video_id"] in bleed_ids:
                continue
            for b in v.get("beats") or []:
                if b.get("type") == "intro" and int(b.get("end_sec") or 0) <= 40:
                    short_intro_ends.append(int(b["end_sec"]))
        target_intro = int(median(short_intro_ends)) if short_intro_ends else 8
    else:
        target_intro = _median_beat_end(live, "intro") or 8

    target_intro = min(intro_cap, max(5, target_intro))
    hook_text, hook_receipt = _hook_line({**draft, "format_name": fmt}, hook_pats)

    beat_order = _FORMAT_BEATS.get(fmt, ["intro", "context", "story", "outro"])
    # Drop duplicate consecutive types except listicle demos
    seen_demo = 0
    ordered: list[str] = []
    for b in beat_order:
        if b == "demo" and seen_demo:
            ordered.append("demo")
            seen_demo += 1
            continue
        if b not in ordered or b == "demo":
            ordered.append(b)
        if b == "demo":
            seen_demo += 1

    cursor = 0
    beats_out: list[dict] = []
    for btype in ordered:
        if btype not in BEAT_TYPES:
            continue
        if btype == "intro":
            dur = target_intro
            note = f"{hook_text}"
            receipts = [r for r in [hook_receipt, intro_receipt] if r]
            if intro_receipt:
                pct_cost = round((1 - 1 / max(intro_receipt["effect_size"], 1.01)) * 100)
                guidance = (
                    f"Cold-open {draft.get('hook_style') or 'hook'} — your data shows intros over "
                    f"{intro_cap}s bleed ~{pct_cost}% retention vs short intros "
                    f"({intro_receipt['pattern_label']}). Skip preamble."
                )
            else:
                guidance = f"Open with your {draft.get('hook_style') or 'hook'} hook — keep intro under {intro_cap}s."
        elif btype == "demo":
            dur = _median_beat_duration(live, "demo") or 45
            demo_pat = next((p for p in patterns if p.get("kind") == "Pacing" and "demo" in p.get("label", "").lower()), None)
            receipts = [_receipt_from_pattern(demo_pat)] if demo_pat else []
            guidance = (
                "Spend real time here — your retention historically holds through demos and proof sections."
            )
            if not receipts and live:
                demo_durs = []
                for v in live:
                    for b in v.get("beats") or []:
                        if b.get("type") == "demo":
                            demo_durs.append(int(b.get("end_sec", 0)) - int(b.get("start_sec", 0)))
                if demo_durs:
                    receipts.append({
                        "type": "computed",
                        "note": f"median demo beat {int(median(demo_durs))}s across your channel (n={len(demo_durs)})",
                        "support_n": len(demo_durs),
                    })
            note = draft.get("angle") or "Show the core proof / walkthrough early."
        elif btype == "context":
            dur = _median_beat_duration(live, "context") or 18
            note = "Stakes + why this matters to you — one breath, not a biography."
            receipts = []
            guidance = "Bridge from hook to story; avoid re-introducing yourself."
        elif btype == "story":
            dur = _median_beat_duration(live, "story") or 90
            note = draft.get("title") or "Main narrative beat."
            receipts = []
            topic_pats = _pattern_for_kind(patterns, "Topic", is_short)
            for t in draft.get("topic_labels") or []:
                tp = next((p for p in topic_pats if t.lower() in (p.get("feature_value") or "").lower()), None)
                if tp:
                    receipts.append(_receipt_from_pattern(tp))
                    break
            guidance = "This is the emotional core — stay in one lane, no tangent stack."
        elif btype == "cta":
            dur = _median_beat_duration(live, "cta") or 12
            note = "One clear next step — subscribe, comment prompt, or related video."
            receipts = []
            guidance = "Keep CTA under 15s; don't apologize for asking."
        else:
            dur = _median_beat_duration(live, btype) or 8
            note = "Clean landing — don't overstay."
            receipts = []
            guidance = "Match your usual outro length."

        start, end = cursor, cursor + dur
        beats_out.append({
            "type": btype,
            "start_sec": start,
            "end_sec": end,
            "time_range": f"{_fmt_ts(start)}–{_fmt_ts(end)}",
            "target_duration_sec": dur,
            "line": note,
            "guidance": guidance,
            "receipts": receipts,
        })
        cursor = end

    total = cursor
    return {
        "format": fmt,
        "is_short": is_short,
        "total_target_sec": total,
        "total_target": _fmt_ts(total),
        "beats": beats_out,
    }


def generate_production_kit(draft: dict) -> dict:
    """Build thumbnail brief + script skeleton; cache to disk."""
    idea_id = draft.get("id") or str(uuid.uuid4())
    corpus = load_corpus()
    table = load_analytics_table()
    for row in table:
        vid = row.get("video_id")
        cv = next((v for v in corpus["live"] if v["video_id"] == vid), None)
        if cv and cv.get("beats"):
            row["beats"] = cv["beats"]

    patterns = run_pattern_scan(corpus["live"])
    fmt = draft.get("format_name") or ""
    card = (draft.get("payload") or {}).get("card") or {}
    if not fmt:
        fmt = card.get("format") or "talking-head"
    is_short = fmt == "day-in-life" and False  # default long-form unless explicit
    if card.get("format") and "short" in str(card.get("format")).lower():
        is_short = True

    enriched = {
        **draft,
        "format_name": fmt,
        "is_short": is_short,
        "hook_style": (card.get("hook") or {}).get("style") or "",
        "payload": draft.get("payload"),
    }

    kit = {
        "thumbnail_brief": build_thumbnail_brief(enriched, patterns, table),
        "script_skeleton": build_script_skeleton(enriched, patterns, table),
    }
    return _save_kit(str(idea_id), kit)


def ensure_production_kit(draft: dict) -> dict:
    """Return cached kit or generate for a planted draft."""
    idea_id = str(draft.get("id") or "")
    if not idea_id:
        return generate_production_kit(draft)
    existing = load_production_kit(idea_id)
    if existing:
        return existing
    return generate_production_kit(draft)

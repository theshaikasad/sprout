"""Concept-art generation on planting — feature-flagged, gradient fallback."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .config import CACHE_DIR, CONCEPT_ART_ENABLED, LLM_API_KEY

ART_DIR = CACHE_DIR / "concept_art"
ART_DIR.mkdir(exist_ok=True)

GRADIENTS = [
    "linear-gradient(135deg, #f3ead7 0%, #c8d4a8 50%, #8fa86e 100%)",
    "linear-gradient(145deg, #fcf7ec 0%, #e8d5b5 40%, #6b8f4e 100%)",
    "linear-gradient(160deg, #f6eedd 0%, #d4c4a0 55%, #47702f 100%)",
]


def concept_art_url(idea_id: str, title: str) -> str:
    """Return a servable /concept-art/ URL, or a gradient fallback for a
    planted idea. The URL (not a raw filesystem path) is what makes this
    actually renderable — see api.py's static mount."""
    if not CONCEPT_ART_ENABLED:
        h = int(hashlib.md5(idea_id.encode()).hexdigest()[:8], 16)
        return GRADIENTS[h % len(GRADIENTS)]

    path = ART_DIR / f"{idea_id}.png"
    if path.exists():
        return f"/concept-art/{idea_id}.png"

    try:
        import base64
        from openai import OpenAI
        client = OpenAI(api_key=LLM_API_KEY)
        resp = client.images.generate(
            model="gpt-image-1",  # dall-e-3 retired; this family returns b64, not a URL
            prompt=(
                f"Ghibli-cozy gouache storybook illustration for a YouTube video idea: {title}. "
                "Warm hand-painted, soft daylight, wood and plant textures, no text, no faces."
            ),
            size="1024x1024",
            n=1,
        )
        path.write_bytes(base64.b64decode(resp.data[0].b64_json))
        return f"/concept-art/{idea_id}.png"
    except Exception as e:
        print(f"concept_art: generation failed for {idea_id!r} — {e}")
        h = int(hashlib.md5(idea_id.encode()).hexdigest()[:8], 16)
        return GRADIENTS[h % len(GRADIENTS)]

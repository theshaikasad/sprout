"""§10a — plain vector RAG vs the killer join, side by side.

Same question through cognee.search(CHUNKS) + a generic LLM answer, vs recall()'s
orchestrated graph traversal. Judges see why this isn't "RAG with extra steps."
"""

import json

from cognee import SearchType
from openai import AsyncOpenAI

from .cognee_env import cognee  # noqa: F401
from .config import EXTRACT_MODEL, LLM_API_KEY
from .recall import gap_finder, suggest

_llm = AsyncOpenAI(api_key=LLM_API_KEY)

# Deliberately NEUTRAL: same model, honest effort, only the retrieval differs.
# The contrast must win structurally (no trend join, no conversion numbers, no
# citations available to this side) — never by telling the model to act dumb.
_RAG_SYSTEM = """You are a helpful assistant. Using ONLY the provided transcript chunks from a
YouTube creator's channel, suggest ONE video they should make next and briefly justify it
(3-4 sentences). If the chunks are thin, give your best general recommendation."""


async def rag_only(query: str) -> dict:
    """Plain CHUNKS retrieval → generic synthesis. No graph join."""
    try:
        chunks = await cognee.search(
            query_text=query,
            query_type=SearchType.CHUNKS,
            top_k=8,
        )
    except Exception:  # store has no DocumentChunks yet (Lane B backfill pending)
        chunks = []
    texts = [str(c)[:600] for c in chunks][:6]
    resp = await _llm.chat.completions.create(
        model=EXTRACT_MODEL,
        messages=[
            {"role": "system", "content": _RAG_SYSTEM},
            {
                "role": "user",
                "content": f"Question: {query}\n\nTranscript chunks:\n"
                + "\n---\n".join(texts or ["(no chunks retrieved)"]),
            },
        ],
    )
    return {
        "mode": "vector_rag",
        "query": query,
        "chunks_used": len(texts),
        "answer": resp.choices[0].message.content or "",
    }


async def contrast(trend_label: str | None = None) -> dict:
    """Side-by-side: RAG answer vs killer-query concept cards on the same trend,
    plus the gap-finder's raw Cypher — two query shapes (a live graph hop, a live
    existential negation over a stored edge) a plain vector search() cannot
    express either way."""
    recall = await suggest(trend_label)
    trend = recall.get("trend") or trend_label or "this week"
    query = f"What should I make this week about {trend}?"
    rag = await rag_only(query)
    graph_card = (recall.get("cards") or [None])[0]
    gaps = await gap_finder(trend)
    return {
        "query": query,
        "trend": trend,
        "rag": rag,
        "graph": {
            "mode": "killer_join",
            "cards": [
                {
                    "title": c.get("title"),
                    "hook": c.get("hook"),
                    "format": c.get("format"),
                    "why": c.get("why"),
                    "citations": c.get("citations", [])[:3],
                }
                for c in recall.get("cards", [])
            ],
            "headline_card": graph_card,
        },
        "gap_finder": {
            "mode": "cypher_anti_join",
            "cypher_query": gaps["cypher_query"],
            "raw_match_count": gaps["raw_match_count"],
            "gaps": gaps["gaps"],
        },
    }

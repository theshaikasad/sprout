"""Phase 0 — Cognee postgres+pgvector smoke test on one dataset.

Usage (with Cloud SQL proxy or direct IP):
  export SPROUT_DATABASE_URL=postgresql+asyncpg://postgres:PASS@127.0.0.1:5432/sprout_app
  export DB_HOST=127.0.0.1 DB_PASSWORD=PASS DB_NAME=cognee_meta
  python -m memory_shield.scripts.phase0_smoke
"""

from __future__ import annotations

import asyncio
import os
import uuid

from memory_shield.config import DEMO_DEFAULT_TREND  # noqa: F401
from memory_shield.cognee_env import cognee
from memory_shield.cognee_context import user_cognee_context
from memory_shield.recall import gap_finder, suggest
from memory_shield.ops import improve


async def main() -> None:
    if not os.getenv("SPROUT_DATABASE_URL"):
        raise SystemExit("Set SPROUT_DATABASE_URL to postgres before running Phase 0")

    from cognee.infrastructure.databases.relational import create_db_and_tables

    await create_db_and_tables()

    from cognee.modules.users.methods import create_user
    from cognee.modules.data.methods import create_dataset

    cognee_user = await create_user(
        email=f"smoke_{uuid.uuid4().hex[:8]}@example.com",
        password=str(uuid.uuid4()),
        is_verified=True,
    )
    dataset = await create_dataset("smoke", cognee_user)
    dataset_id = dataset.id
    user_id = cognee_user.id

    async with user_cognee_context(dataset_id=dataset_id, user_id=user_id):
        await cognee.remember(
            "Sprout smoke test: personal essay videos convert 2x for slow-living creators.",
            dataset_name="smoke",
        )
        await cognee.cognify()

        results = await cognee.search("what converts for slow living")
        print("search:", len(results), "results")

        try:
            cards = await suggest(DEMO_DEFAULT_TREND)
            print("suggest cards:", len(cards.get("cards", [])))
        except ValueError as exc:
            print("suggest skipped (minimal graph):", exc)

        gaps = await gap_finder()
        print("gap_finder topics:", len(gaps))
        print("Phase 0 smoke test passed")


if __name__ == "__main__":
    asyncio.run(main())

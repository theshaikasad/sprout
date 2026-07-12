# Sprout backend — FastAPI + Cognee, single-tenant demo mode on Cloud Run.
# The demo world ships pre-built in the image: kuzu+lancedb store (demo_graph/)
# and caches (demo_seed/). No Cloud SQL in the serving path.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_shield ./memory_shield
# Frozen demo world (gitignored .cognee/ and .cache/ are local-only; these are
# their committed snapshots — rebuild with scripts/snapshot-demo-world.sh).
COPY demo_graph/ ./.cognee/
COPY demo_seed/ ./.cache/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "memory_shield.api:app", "--host", "0.0.0.0", "--port", "8080"]

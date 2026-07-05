# Sprout backend — FastAPI + Cognee (postgres or local kuzu fallback).
# Production: Cloud Run + Cloud SQL. Env via Secret Manager.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory_shield ./memory_shield
# Demo corpus + analytics for Cloud Run (gitignored .cache/ is local-only).
COPY demo_seed/ ./.cache/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "memory_shield.api:app", "--host", "0.0.0.0", "--port", "8080"]

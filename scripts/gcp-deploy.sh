#!/usr/bin/env bash
# Deploy Sprout backend + frontend to Cloud Run.
# Prefer GitHub Actions (.github/workflows/deploy.yml) for production.
set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-sprout-cognee-hackathon}"
REGION="${GCP_REGION:-us-central1}"
IMAGE_BACKEND="us-central1-docker.pkg.dev/${PROJECT}/sprout/backend:latest"
IMAGE_FRONTEND="us-central1-docker.pkg.dev/${PROJECT}/sprout/frontend:latest"
API_BASE="${NEXT_PUBLIC_API_BASE:-https://api.sprout.asad.codes}"
FRONTEND_URL="${FRONTEND_URL:-https://sprout.asad.codes}"
CORS="${CORS_ORIGINS:-https://sprout.asad.codes,http://localhost:3000}"

gcloud artifacts repositories describe sprout --location="$REGION" --project="$PROJECT" 2>/dev/null \
  || gcloud artifacts repositories create sprout --repository-format=docker --location="$REGION" --project="$PROJECT"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Building backend..."
gcloud builds submit "$ROOT/backend" --tag "$IMAGE_BACKEND" --project="$PROJECT"

echo "Building frontend..."
gcloud builds submit "$ROOT/frontend" \
  --config "$ROOT/frontend/cloudbuild.yaml" \
  --project="$PROJECT" \
  --substitutions="_API_BASE=${API_BASE},_FIREBASE_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY:-},_FIREBASE_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN:-},_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID:-},_FIREBASE_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID:-}"

echo "Deploying backend (single-tenant demo mode — kuzu store baked into the image)..."
# max-instances=1: the kuzu graph is a single-writer store inside the container.
gcloud run deploy sprout-backend \
  --image "$IMAGE_BACKEND" \
  --region "$REGION" \
  --project "$PROJECT" \
  --min-instances 1 \
  --max-instances 1 \
  --cpu 2 --memory 2Gi \
  --timeout 3600 \
  --allow-unauthenticated \
  --clear-cloudsql-instances \
  --set-env-vars "^##^FRONTEND_URL=${FRONTEND_URL}##CORS_ORIGINS=${CORS}##CREATOR_HANDLE=${CREATOR_HANDLE:-@LanaBlakely}##CHAT_MODEL=gpt-4o-mini##GOOGLE_OAUTH_REDIRECT_URI=${API_BASE}/auth/youtube/callback" \
  --set-secrets="LLM_API_KEY=sprout-llm-api-key:latest,YOUTUBE_API_KEY=sprout-youtube-api-key:latest,TELEGRAM_BOT_TOKEN=sprout-telegram-bot-token:latest,GOOGLE_OAUTH_CLIENT_ID=sprout-google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=sprout-google-oauth-client-secret:latest,CRON_SECRET=sprout-cron-secret:latest,TELEGRAM_LINK_SECRET=sprout-telegram-link-secret:latest,FIREBASE_SERVICE_ACCOUNT_JSON=sprout-firebase-service-account:latest"

gcloud run deploy sprout-frontend \
  --image "$IMAGE_FRONTEND" \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated

echo "Done. Run ./scripts/bootstrap-gcp-secrets.sh first if secrets are missing."
echo "Prefer GitHub Actions deploy — see .github/DEPLOY.md"

#!/usr/bin/env bash
# One-time: push runtime secrets from local .env → GCP Secret Manager.
# GitHub Actions deploy reads these via Cloud Run --set-secrets (never from workflow logs).
#
# Usage (from repo root, after gcloud auth login):
#   source .env
#   ./scripts/bootstrap-gcp-secrets.sh
#
# Requires: gcloud, openssl. Run once per environment rotation.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PROJECT="${GCP_PROJECT_ID:-sprout-cognee-hackathon}"
REGION="${GCP_REGION:-us-central1}"
INSTANCE="${CLOUD_SQL_INSTANCE:-sprout-db}"

if [[ -z "${DB_PASSWORD:-}" && -f /tmp/sprout_db_pass.txt ]]; then
  DB_PASSWORD=$(cat /tmp/sprout_db_pass.txt)
fi

: "${DB_PASSWORD:?Set DB_PASSWORD or create /tmp/sprout_db_pass.txt}"
: "${LLM_API_KEY:?Set LLM_API_KEY}"
: "${YOUTUBE_API_KEY:?Set YOUTUBE_API_KEY}"

CONN="${PROJECT}:${REGION}:${INSTANCE}"
DATABASE_URL="postgresql+asyncpg://postgres:${DB_PASSWORD}@/sprout_app?host=/cloudsql/${CONN}"

upsert_secret() {
  local name="$1"
  local value="$2"
  if gcloud secrets describe "$name" --project="$PROJECT" &>/dev/null; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --project="$PROJECT" --data-file=-
  else
    printf '%s' "$value" | gcloud secrets create "$name" --project="$PROJECT" --data-file=-
  fi
  echo "  ✓ $name"
}

echo "Bootstrapping secrets in project $PROJECT..."

upsert_secret sprout-db-root-pass "$DB_PASSWORD"
upsert_secret sprout-database-url "$DATABASE_URL"
upsert_secret sprout-llm-api-key "$LLM_API_KEY"
upsert_secret sprout-youtube-api-key "$YOUTUBE_API_KEY"
upsert_secret sprout-telegram-bot-token "${TELEGRAM_BOT_TOKEN:-}"
upsert_secret sprout-google-oauth-client-id "${GOOGLE_OAUTH_CLIENT_ID:-}"
upsert_secret sprout-google-oauth-client-secret "${GOOGLE_OAUTH_CLIENT_SECRET:-}"

if [[ -n "${FIREBASE_SERVICE_ACCOUNT_JSON:-}" ]]; then
  upsert_secret sprout-firebase-service-account "$FIREBASE_SERVICE_ACCOUNT_JSON"
elif [[ -n "${FIREBASE_SERVICE_ACCOUNT_FILE:-}" ]]; then
  SA_FILE="$FIREBASE_SERVICE_ACCOUNT_FILE"
  [[ "$SA_FILE" != /* ]] && SA_FILE="$ROOT/$SA_FILE"
  if [[ -f "$SA_FILE" ]]; then
    upsert_secret sprout-firebase-service-account "$(cat "$SA_FILE")"
  else
    echo "  ⚠ FIREBASE_SERVICE_ACCOUNT_FILE not found: $SA_FILE"
  fi
fi
upsert_secret sprout-cron-secret "${CRON_SECRET:-$(openssl rand -hex 24)}"
upsert_secret sprout-telegram-link-secret "${TELEGRAM_LINK_SECRET:-$(openssl rand -hex 24)}"

echo ""
echo "Granting Secret Manager access to Cloud Run runtime service account..."
RUNTIME_SA="${CLOUD_RUN_RUNTIME_SA:-$(gcloud iam service-accounts list \
  --project="$PROJECT" \
  --filter='email ~ compute@developer' \
  --format='value(email)' | head -1)}"

if [[ -n "$RUNTIME_SA" ]]; then
  for secret in sprout-db-root-pass sprout-database-url sprout-llm-api-key sprout-youtube-api-key \
    sprout-telegram-bot-token sprout-google-oauth-client-id sprout-google-oauth-client-secret \
    sprout-cron-secret sprout-telegram-link-secret sprout-firebase-service-account; do
    gcloud secrets add-iam-policy-binding "$secret" \
      --project="$PROJECT" \
      --member="serviceAccount:${RUNTIME_SA}" \
      --role="roles/secretmanager.secretAccessor" \
      --quiet >/dev/null 2>&1 || true
  done
  echo "  ✓ secretAccessor for $RUNTIME_SA"
else
  echo "  ⚠ Could not detect runtime SA — grant secretAccessor manually (see .github/DEPLOY.md)"
fi

echo ""
echo "Done. Next: ./scripts/setup-github-wif.sh"

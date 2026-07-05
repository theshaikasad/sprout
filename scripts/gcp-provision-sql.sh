#!/usr/bin/env bash
# Provision Cloud SQL + secrets for Sprout multi-user stack.
set -euo pipefail

PROJECT="${PROJECT:-sprout-cognee-hackathon}"
REGION="${REGION:-us-central1}"
INSTANCE="${INSTANCE:-sprout-db}"

if ! gcloud sql instances describe "$INSTANCE" --project="$PROJECT" &>/dev/null; then
  DB_PASS="${DB_PASS:-$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)}"
  echo "Creating Cloud SQL instance $INSTANCE..."
  gcloud sql instances create "$INSTANCE" \
    --project="$PROJECT" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --root-password="$DB_PASS" \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00
  echo -n "$DB_PASS" > /tmp/sprout_db_pass.txt
  echo "Password saved to /tmp/sprout_db_pass.txt"
else
  echo "Instance $INSTANCE already exists"
  DB_PASS="${DB_PASS:-$(cat /tmp/sprout_db_pass.txt 2>/dev/null || true)}"
fi

echo "Waiting for RUNNABLE..."
for i in $(seq 1 60); do
  STATE=$(gcloud sql instances describe "$INSTANCE" --project="$PROJECT" --format="value(state)")
  if [[ "$STATE" == "RUNNABLE" ]]; then break; fi
  sleep 15
done

gcloud sql databases create sprout_app --instance="$INSTANCE" --project="$PROJECT" 2>/dev/null || true
gcloud sql databases create cognee_meta --instance="$INSTANCE" --project="$PROJECT" 2>/dev/null || true

if [[ -n "${DB_PASS:-}" ]]; then
  gcloud secrets describe sprout-db-root-pass --project="$PROJECT" &>/dev/null \
    || echo -n "$DB_PASS" | gcloud secrets create sprout-db-root-pass --project="$PROJECT" --data-file=-
fi

IP=$(gcloud sql instances describe "$INSTANCE" --project="$PROJECT" --format="value(ipAddresses[0].ipAddress)")
echo "Cloud SQL IP: $IP"
echo "Enable pgvector: connect and run CREATE EXTENSION vector; on cognee_meta + each dataset DB"

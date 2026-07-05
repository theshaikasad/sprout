#!/usr/bin/env bash
# Grant github-deployer everything GitHub Actions deploy needs (idempotent).
# Run once from a machine with project Owner/Editor (local gcloud auth).
#
# Usage:
#   ./scripts/grant-github-deployer-iam.sh

set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-sprout-cognee-hackathon}"
SA_NAME="github-deployer"
SA="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
CLOUDBUILD_BUCKET="${PROJECT}_cloudbuild"

echo "Project: ${PROJECT}"
echo "Deploy SA: ${SA}"

for role in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/cloudbuild.builds.editor \
  roles/iam.serviceAccountUser \
  roles/secretmanager.secretAccessor \
  roles/secretmanager.viewer \
  roles/serviceusage.serviceUsageConsumer \
  roles/storage.admin; do
  echo "  + ${role}"
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${SA}" \
    --role="$role" \
    --quiet >/dev/null
done

# gcloud builds submit uploads source to gs://PROJECT_cloudbuild
echo "  + storage.objectAdmin on gs://${CLOUDBUILD_BUCKET}"
gsutil iam ch "serviceAccount:${SA}:roles/storage.objectAdmin" "gs://${CLOUDBUILD_BUCKET}" 2>/dev/null \
  || echo "    (bucket may not exist yet — Cloud Build creates it on first build; storage.admin above covers it)"

# Cloud Build runs as the default Cloud Build service account
echo "  + serviceAccountUser on ${CLOUDBUILD_SA}"
gcloud iam service-accounts add-iam-policy-binding "$CLOUDBUILD_SA" \
  --project="$PROJECT" \
  --member="serviceAccount:${SA}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null

echo ""
echo "Done. Re-run GitHub Actions → Deploy (or push to main)."

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
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
CLOUDBUILD_BUCKET="${PROJECT}_cloudbuild"

echo "Project: ${PROJECT}"
echo "Deploy SA: ${SA}"

echo "Enabling required APIs (creates Cloud Build SA on first enable)..."
gcloud services enable \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT" \
  --quiet

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
echo "  + storage.objectAdmin on gs://${CLOUDBUILD_BUCKET} (if bucket exists)"
if gsutil ls -b "gs://${CLOUDBUILD_BUCKET}" >/dev/null 2>&1; then
  gsutil iam ch "serviceAccount:${SA}:roles/storage.objectAdmin" "gs://${CLOUDBUILD_BUCKET}"
else
  echo "    bucket not created yet — roles/storage.admin on the project covers the first build"
fi

# Optional: let deploy SA act as build runtime SAs (legacy Cloud Build SA may not exist on new projects)
bind_sa_user() {
  local target_sa="$1"
  if gcloud iam service-accounts describe "$target_sa" --project="$PROJECT" >/dev/null 2>&1; then
    echo "  + serviceAccountUser on ${target_sa}"
    gcloud iam service-accounts add-iam-policy-binding "$target_sa" \
      --project="$PROJECT" \
      --member="serviceAccount:${SA}" \
      --role="roles/iam.serviceAccountUser" \
      --quiet >/dev/null
  else
    echo "  ~ skip ${target_sa} (not provisioned — OK on newer GCP projects)"
  fi
}

bind_sa_user "$CLOUDBUILD_SA"
bind_sa_user "$COMPUTE_SA"

echo ""
echo "Done. Re-run GitHub Actions → Deploy (or push to main)."

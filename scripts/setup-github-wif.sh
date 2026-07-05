#!/usr/bin/env bash
# Configure Workload Identity Federation for GitHub Actions → GCP deploy.
# Prints the two values to add as GitHub Secrets.
#
# Usage:
#   export GITHUB_REPO=your-org/cognee-hackathon
#   ./scripts/setup-github-wif.sh

set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-sprout-cognee-hackathon}"
GITHUB_REPO="${GITHUB_REPO:?Set GITHUB_REPO=owner/repo (e.g. theshaikasad/sprout)}"

SA_NAME="github-deployer"
SA="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')

gcloud iam service-accounts create "$SA_NAME" \
  --project="$PROJECT" \
  --display-name="GitHub Actions deployer" 2>/dev/null || true

for role in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/cloudbuild.builds.editor \
  roles/iam.serviceAccountUser \
  roles/secretmanager.secretAccessor \
  roles/secretmanager.viewer \
  roles/serviceusage.serviceUsageConsumer \
  roles/storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${SA}" \
    --role="$role" \
    --quiet >/dev/null
done

# gcloud builds submit stages source in gs://PROJECT_cloudbuild
gcloud iam service-accounts add-iam-policy-binding "${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --project="$PROJECT" \
  --member="serviceAccount:${SA}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null 2>/dev/null || true

gcloud iam workload-identity-pools create github-pool \
  --project="$PROJECT" --location=global \
  --display-name="GitHub pool" 2>/dev/null || true

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project="$PROJECT" --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_REPO%%/*}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" 2>/dev/null || true

gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --project="$PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}" \
  --quiet >/dev/null

POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --project="$PROJECT" --location=global --format='value(name)')

echo ""
echo "Add these GitHub Secrets (repo → Settings → Secrets → Actions):"
echo ""
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=${POOL_ID}/providers/github-provider"
echo "GCP_SERVICE_ACCOUNT=${SA}"
echo ""
echo "See .github/DEPLOY.md for full setup."

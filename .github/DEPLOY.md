# GitHub Actions deployment

Deploy Sprout to Cloud Run on push to `main` or via **Actions → Deploy → Run workflow**.

Runtime API keys **never** go in GitHub Secrets as plain deploy env vars. They live in **GCP Secret Manager** and mount into Cloud Run at runtime. GitHub only holds credentials to *authenticate* to GCP.

## 1. GCP Secret Manager (one-time)

From repo root with `.env` loaded:

```bash
export DB_PASSWORD='your-cloud-sql-postgres-password'
source .env
chmod +x scripts/bootstrap-gcp-secrets.sh
./scripts/bootstrap-gcp-secrets.sh
```

Creates: `sprout-db-root-pass`, `sprout-database-url`, `sprout-llm-api-key`, `sprout-youtube-api-key`, `sprout-telegram-bot-token`, `sprout-google-oauth-client-id`, `sprout-google-oauth-client-secret`, `sprout-cron-secret`, `sprout-telegram-link-secret`.

Grant the Cloud Run runtime service account `roles/secretmanager.secretAccessor` on each secret (script prints commands).

## 2. Workload Identity Federation (recommended — no SA JSON in GitHub)

Run once (replace `YOUR_GITHUB_ORG` / repo name):

```bash
export PROJECT_ID=sprout-cognee-hackathon
export GITHUB_REPO="YOUR_GITHUB_ORG/cognee-hackathon"   # owner/repo

gcloud iam service-accounts create github-deployer \
  --project="$PROJECT_ID" \
  --display-name="GitHub Actions deployer"

SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

for role in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/cloudbuild.builds.editor \
  roles/iam.serviceAccountUser \
  roles/secretmanager.secretAccessor \
  roles/secretmanager.viewer \
  roles/serviceusage.serviceUsageConsumer \
  roles/storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA}" --role="$role"
done

gcloud iam workload-identity-pools create github-pool \
  --project="$PROJECT_ID" --location=global \
  --display-name="GitHub pool" 2>/dev/null || true

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project="$PROJECT_ID" --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com" 2>/dev/null || true

gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"

echo ""
echo "Add these GitHub Secrets (Settings → Secrets and variables → Actions):"
POOL_ID=$(gcloud iam workload-identity-pools describe github-pool --project="$PROJECT_ID" --location=global --format='value(name)')
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER=${POOL_ID}/providers/github-provider"
echo "  GCP_SERVICE_ACCOUNT=${SA}"
```

## 3. GitHub repository configuration

### Secrets (Settings → Secrets → Actions)

| Secret | Purpose |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name (from step 2) |
| `GCP_SERVICE_ACCOUNT` | `github-deployer@….iam.gserviceaccount.com` |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Baked into frontend Docker build |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Baked into frontend Docker build |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Baked into frontend Docker build |

### Variables (Settings → Variables → Actions) — non-secret

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | `sprout-cognee-hackathon` | GCP project |
| `GCP_REGION` | `us-central1` | Cloud Run region |
| `CLOUD_SQL_INSTANCE` | `sprout-db` | Cloud SQL instance name |
| `FRONTEND_URL` | `https://sprout.asad.codes` | OAuth redirects |
| `NEXT_PUBLIC_API_BASE` | `https://api.sprout.asad.codes` | Frontend API URL |
| `CORS_ORIGINS` | `https://sprout.asad.codes,http://localhost:3000` | Backend CORS |
| `CREATOR_HANDLE` | `@LanaBlakely` | Demo corpus handle |

### Environment

Create a **`production`** environment (Settings → Environments) to require manual approval before deploy if desired.

## 4. Workflows

| File | Trigger | What it does |
|---|---|---|
| `.github/workflows/ci.yml` | PR + push to main | Backend import test, frontend build |
| `.github/workflows/deploy.yml` | push to main, manual | CI → build images → deploy Cloud Run → `/health` smoke test |

## 5. Fallback: service account key (less safe)

If WIF setup is blocked, store the JSON key as `GCP_SA_KEY` and change the auth step in `deploy.yml` to:

```yaml
- uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

Prefer WIF — keys don't rotate automatically and are easier to leak.

## 6. Troubleshooting

### `forbidden from accessing the bucket [PROJECT_cloudbuild]`

`gcloud builds submit` uploads source to the default Cloud Build bucket and needs `serviceusage.services.use` plus storage access. Grant the deploy SA:

```bash
chmod +x scripts/grant-github-deployer-iam.sh
./scripts/grant-github-deployer-iam.sh
```

Or manually add `roles/serviceusage.serviceUsageConsumer` and `roles/storage.admin` to `github-deployer@….iam.gserviceaccount.com`. The legacy `{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com` may not exist on newer GCP projects — that is OK; `storage.admin` on the deploy SA is what matters.

If the grant script errors on the Cloud Build SA, pull latest `main` and re-run — it now skips missing SAs.

### `PERMISSION_DENIED: secretmanager.secrets.get`

The deploy workflow verifies secrets with `gcloud secrets versions access` (needs `secretAccessor`). Older workflow versions used `gcloud secrets describe`, which needs `secretmanager.viewer`. If you still see this on an old run, re-run deploy after pulling latest `main`, or grant viewer to the deploy SA:

```bash
gcloud projects add-iam-policy-binding sprout-cognee-hackathon \
  --member="serviceAccount:github-deployer@sprout-cognee-hackathon.iam.gserviceaccount.com" \
  --role="roles/secretmanager.viewer"
```

## 7. Manual deploy (local)

```bash
./scripts/gcp-provision-sql.sh    # once
./scripts/bootstrap-gcp-secrets.sh
./scripts/gcp-deploy.sh           # or push to main and let Actions run
```

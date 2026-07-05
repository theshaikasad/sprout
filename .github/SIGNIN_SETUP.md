# Sign-in setup (Firebase + YouTube OAuth)

Sign-in is **two steps** for real users:

1. **Firebase** — "Continue with Google" (identity only)
2. **YouTube OAuth** — "Connect YouTube" on signup (analytics access)

Demo mode (`/studio` without sign-in) works without any of this.

---

## Part A — Firebase (frontend sign-in button)

### 1. Create Firebase project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. **Add project** (can link to `sprout-cognee-hackathon` GCP project or be separate)
3. Skip Analytics if you want — not required

### 2. Enable Google sign-in

1. **Build → Authentication → Get started**
2. **Sign-in method → Google → Enable → Save**

### 3. Register web app

1. Project overview → **Add app → Web** (`</>`)
2. Copy the config values:

```
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=....firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

### 4. Authorized domains

**Authentication → Settings → Authorized domains** — add:

- `localhost`
- `sprout.asad.codes`
- `sprout-frontend-4veu64ey5q-uc.a.run.app` (until custom domain HTTPS works)

### 5. Service account for backend (token verification)

1. **Project settings → Service accounts**
2. **Generate new private key** → saves a JSON file
3. Add to repo root `.env` (do not commit):

```bash
export FIREBASE_SERVICE_ACCOUNT_FILE=/path/to/firebase-adminsdk-xxxxx.json
```

---

## Part B — Google OAuth (YouTube + Analytics)

This is a **separate** OAuth client from Firebase — Sprout needs refresh tokens for the Analytics API.

### 1. Create OAuth client

1. [Google Cloud Console](https://console.cloud.google.com/) → project `sprout-cognee-hackathon`
2. **APIs & Services → Credentials → Create credentials → OAuth client ID**
3. If prompted, configure **OAuth consent screen**:
   - User type: **External**
   - App name: Sprout
   - Add your email as test user (Testing mode = up to 100 users, no Google review)
4. Application type: **Web application**
5. **Authorized JavaScript origins:**
   - `https://sprout.asad.codes`
   - `https://sprout-frontend-4veu64ey5q-uc.a.run.app`
   - `http://localhost:3000`
6. **Authorized redirect URIs:**
   - `https://api.sprout.asad.codes/auth/youtube/callback`
   - `https://sprout-backend-4veu64ey5q-uc.a.run.app/auth/youtube/callback` (fallback)
7. Copy **Client ID** and **Client secret**

### 2. Enable APIs

**APIs & Services → Library** — enable:

- YouTube Data API v3 (you already have a key)
- **YouTube Analytics API**

### 3. Add to `.env`

```bash
GOOGLE_OAUTH_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
GOOGLE_OAUTH_REDIRECT_URI=https://api.sprout.asad.codes/auth/youtube/callback
```

Use the `run.app` API URL in `REDIRECT_URI` if `api.sprout.asad.codes` HTTPS isn't ready yet.

---

## Part C — Deploy to production

### 1. Update `.env` with all keys, then push secrets to GCP

```bash
cd /Users/asad/Projects/cognee-hackathon
export DB_PASSWORD=$(cat /tmp/sprout_db_pass.txt)
export FIREBASE_SERVICE_ACCOUNT_FILE=/path/to/your-firebase-key.json
# ensure .env has GOOGLE_OAUTH_* and you exported Firebase file above
./scripts/bootstrap-gcp-secrets.sh
```

### 2. Rebuild frontend (Firebase keys are baked in at build time)

```bash
export NEXT_PUBLIC_API_BASE=https://api.sprout.asad.codes   # or run.app backend URL
export NEXT_PUBLIC_FIREBASE_API_KEY=...
export NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
export NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
export NEXT_PUBLIC_FIREBASE_APP_ID=...

gcloud builds submit frontend \
  --config frontend/cloudbuild.yaml \
  --project sprout-cognee-hackathon \
  --substitutions="_API_BASE=${NEXT_PUBLIC_API_BASE},_FIREBASE_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY},_FIREBASE_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN},_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID},_FIREBASE_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID},_IMAGE_TAG=signin"

gcloud run deploy sprout-frontend \
  --image us-central1-docker.pkg.dev/sprout-cognee-hackathon/sprout/frontend:signin \
  --region us-central1 --project sprout-cognee-hackathon --allow-unauthenticated
```

### 3. Redeploy backend (picks up OAuth + Firebase secrets)

```bash
./scripts/gcp-deploy.sh
```

Or redeploy backend only if frontend image already built.

---

## Verify

1. Open signup page — should **not** say "demo mode — Firebase keys not configured"
2. Click **Continue with Google** → Firebase popup works
3. Click **Connect YouTube** → Google consent → redirects back with your channel
4. **Build my memory** → onboarding starts

### Quick API checks

```bash
# Backend sees OAuth (should not 503)
curl -H "Authorization: Bearer FAKE" https://api.sprout.asad.codes/auth/youtube/url
# → 401 invalid token (good) not 503 OAuth not configured

# With real Firebase token from browser devtools:
# curl -H "Authorization: Bearer <idToken>" https://api.../auth/youtube/url
# → {"url":"https://accounts.google.com/..."}
```

---

## Common failures

| Symptom | Fix |
|---|---|
| "demo mode" on signup | Rebuild frontend with `NEXT_PUBLIC_FIREBASE_*` |
| 503 Firebase not configured | Run bootstrap + redeploy backend with `sprout-firebase-service-account` |
| 503 Google OAuth not configured | Add `GOOGLE_OAUTH_*` to `.env`, re-run bootstrap, redeploy backend |
| OAuth redirect mismatch | Redirect URI in Google Console must **exactly** match `GOOGLE_OAUTH_REDIRECT_URI` |
| popup blocked / unauthorized domain | Add domain in Firebase authorized domains |
| Analytics scope denied | Add yourself as **test user** on OAuth consent screen |

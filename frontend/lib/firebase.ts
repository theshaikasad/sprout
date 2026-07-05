/* Firebase Auth (Google provider) — real sign-in when the NEXT_PUBLIC_FIREBASE_*
   keys are configured, graceful demo fallback when they aren't, so the app never
   blocks on missing infra. Setup: see frontend/.env.local.example. */

import { getApps, initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type Auth,
  type User,
} from "firebase/auth";

const cfg = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const firebaseEnabled = Boolean(
  cfg.apiKey && cfg.authDomain && cfg.projectId && cfg.appId,
);

function auth(): Auth | null {
  if (!firebaseEnabled) return null;
  const app = getApps()[0] ?? initializeApp(cfg);
  return getAuth(app);
}

export async function getIdToken(): Promise<string | null> {
  const a = auth();
  if (!a?.currentUser) return null;
  return a.currentUser.getIdToken();
}

/** Opens Google's own popup. Returns null in demo mode (no keys). */
export async function signInWithGoogle(): Promise<User | null> {
  const a = auth();
  if (!a) return null;
  const res = await signInWithPopup(a, new GoogleAuthProvider());
  return res.user;
}

export function watchAuth(cb: (u: User | null) => void): () => void {
  const a = auth();
  if (!a) {
    cb(null);
    return () => {};
  }
  return onAuthStateChanged(a, cb);
}

export async function signOutUser(): Promise<void> {
  const a = auth();
  if (a) await signOut(a);
}

export type { User };

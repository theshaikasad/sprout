"use client";

/* eslint-disable @next/next/no-img-element */

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { api } from "@/lib/api";
import { firebaseEnabled, signInWithGoogle } from "@/lib/firebase";
import ConnectTelegram from "@/components/ConnectTelegram";
import { Logo } from "@/components/Logo";

type Step = "start" | "consent" | "channel" | "building" | "reveal";
type PreviewTier = "empty" | "warming" | "established";

type Profile = { name: string; email: string; photo: string | null };

const BUILD_STAGES = [
  { key: "fetching", label: "REMEMBER · fetching channel, competitors & trends" },
  { key: "enriching", label: "EXTRACT · format + topics + hook per video" },
  { key: "ingesting", label: "COGNIFY · building the knowledge graph" },
  { key: "done", label: "MEMORY BUILT" },
] as const;

const ORDER: Record<string, number> = {
  idle: -1, fetching: 0, enriching: 1, ingesting: 2, done: 3, error: -2,
};

const READS: { on: boolean; text: string; soon?: boolean }[] = [
  { on: true, text: "Your channel and its public videos" },
  { on: true, text: "Video performance — views, publish dates, formats" },
  { on: true, text: "Niche competitors and live trends (public)" },
  { on: true, text: "YouTube Studio analytics — retention, CTR, traffic (read-only)" },
];

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.2C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.2C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

const slide = {
  initial: { opacity: 0, x: 24 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -24 },
  transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
};

function tierFromCount(count: number | null | undefined): PreviewTier {
  if (count == null || count <= 0) return "empty";
  if (count < 10) return "warming";
  return "established";
}

export default function SignupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("start");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [channel, setChannel] = useState<{ title: string; avatar: string; subscribers: number } | null>(null);
  const [videoCount, setVideoCount] = useState<number | null>(null);
  const [previewTier, setPreviewTier] = useState<PreviewTier>("established");
  const [declaredNiche, setDeclaredNiche] = useState("");
  const [nicheInput, setNicheInput] = useState("");
  const [genreSummary, setGenreSummary] = useState("");
  const [useBacktestReveal, setUseBacktestReveal] = useState(true);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("idle");
  const [detail, setDetail] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);
  const [memoryReady, setMemoryReady] = useState(false);

  useEffect(() => {
    api
      .library()
      .then((lib) => {
        if (lib.live_videos.length >= 5) setMemoryReady(true);
      })
      .catch(() => {});
  }, []);

  async function refreshOnboardingPreview() {
    try {
      const s = await api.onboardingStatus();
      if (s.channel) setChannel(s.channel);
      const count = s.channel_video_count ?? s.channel?.video_count ?? null;
      if (count != null) setVideoCount(count);
      setPreviewTier(s.preview_tier ?? tierFromCount(count));
      if (s.declared_niche) {
        setDeclaredNiche(s.declared_niche);
        setNicheInput(s.declared_niche);
      }
      if (s.genre?.summary) setGenreSummary(s.genre.summary);
      if (s.use_backtest_reveal != null) setUseBacktestReveal(s.use_backtest_reveal);
    } catch {
      /* demo / not signed in */
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthError = params.get("oauth_error");
    const oauthChannel = params.get("oauth_channel");
    const oauthVideoCount = params.get("video_count");
    if (oauthError) {
      setError(oauthError);
      setStep("consent");
      return;
    }
    if (oauthChannel) {
      setChannel({ title: oauthChannel, avatar: "", subscribers: 0 });
      if (oauthVideoCount != null) {
        const n = parseInt(oauthVideoCount, 10);
        if (!Number.isNaN(n)) {
          setVideoCount(n);
          setPreviewTier(tierFromCount(n));
        }
      }
      setStep("channel");
      window.history.replaceState({}, "", "/signup");
      refreshOnboardingPreview();
    }
  }, []);

  async function google() {
    setError("");
    setAuthBusy(true);
    try {
      const user = await signInWithGoogle();
      setProfile(
        user
          ? {
              name: user.displayName ?? "Creator",
              email: user.email ?? "",
              photo: user.photoURL,
            }
          : { name: "Creator", email: "demo mode — no Firebase keys", photo: null },
      );
      setStep("consent");
    } catch (e) {
      setError(e instanceof Error ? e.message : "sign-in failed");
    } finally {
      setAuthBusy(false);
    }
  }

  async function connectYouTube() {
    setError("");
    try {
      if (firebaseEnabled) {
        const { url } = await api.youtubeAuthUrl();
        window.location.href = url;
        return;
      }
      setStep("channel");
      setPreviewTier("established");
    } catch (e) {
      setError(e instanceof Error ? e.message : "YouTube connect failed");
    }
  }

  async function saveNicheAndBuild() {
    setError("");
    if (previewTier === "empty" && !nicheInput.trim()) {
      setError("Tell Sprout what your channel is about — even one sentence helps.");
      return;
    }
    try {
      if (previewTier === "empty" && nicheInput.trim()) {
        const res = await api.onboardingNiche(nicheInput.trim());
        setDeclaredNiche(res.declared_niche);
      }
      await startBuild();
    } catch (e) {
      setError(e instanceof Error ? e.message : "couldn't save niche");
    }
  }

  async function startBuild() {
    setError("");
    try {
      if (firebaseEnabled) {
        await api.onboardingStart();
      } else {
        await api.connect();
      }
      const s = await api.onboardingStatus().catch(() => api.connectStatus());
      if (s.channel) setChannel(s.channel);
      setStep("building");
    } catch (e) {
      setError(e instanceof Error ? e.message : "couldn't start onboarding");
    }
  }

  useEffect(() => {
    if (step !== "building") return;
    poll.current = setInterval(async () => {
      try {
        const s = await api.onboardingStatus().catch(() => api.connectStatus());
        setStage(s.stage);
        setDetail(s.detail);
        const status = s as { elapsed?: number };
        setElapsed(status.elapsed ?? elapsed);
        if ("genre" in s && s.genre?.summary) setGenreSummary(s.genre.summary);
        if ("use_backtest_reveal" in s && s.use_backtest_reveal != null) {
          setUseBacktestReveal(s.use_backtest_reveal);
        }
        if (s.stage === "done") {
          clearInterval(poll.current!);
          if ("use_backtest_reveal" in s && s.use_backtest_reveal === false) {
            setStep("reveal");
          } else {
            setTimeout(() => router.push("/studio?proof=1"), 1200);
          }
        }
        if (s.stage === "error") {
          clearInterval(poll.current!);
          setError(s.error || s.detail);
          setStep("channel");
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return () => clearInterval(poll.current!);
  }, [step, router, elapsed]);

  const at = ORDER[stage] ?? -1;
  const isColdStart = previewTier === "empty" || previewTier === "warming";

  return (
    <main className="relative z-10 mx-auto grid min-h-screen max-w-5xl items-center gap-12 px-6 py-16 lg:grid-cols-[1.1fr_1fr]">
      <div>
        <a href="/">
          <Logo />
        </a>
        <h1 className="display mt-8 text-5xl leading-[1.05]">
          Stop checking analytics.
          <br />
          <span className="serif-accent text-accent">Start growing videos.</span>
        </h1>
        <p className="mt-5 max-w-md leading-relaxed text-dim">
          Connect your channel once. The memory watches your niche — your
          numbers, your competitors, what&apos;s trending — and tells you the one
          thing that matters each day.
        </p>
        <ul className="mt-6 space-y-2.5 text-sm text-dim">
          {[
            "A morning briefing instead of a dashboard",
            isColdStart
              ? "Trend-based starters until your catalog grows — then cited patterns"
              : "Concepts cited to videos that actually converted",
            "It sharpens automatically when your uploads perform",
          ].map((t) => (
            <li key={t} className="flex items-start gap-2.5">
              <span className="mt-0.5 text-accent">✓</span>
              {t}
            </li>
          ))}
        </ul>
        <p className="mt-8 font-mono text-[11px] text-faint">
          YouTube today · Facebook · Instagram · TikTok next
        </p>
      </div>

      <div className="panel relative overflow-hidden p-6">
        <AnimatePresence mode="wait">
          {step === "start" && (
            <motion.div key="start" {...slide}>
              <p className="label">create your studio</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Sign up</h2>
              <p className="mt-2 text-sm leading-relaxed text-dim">
                One click with Google. We never see your password, and you
                approve exactly what the memory can read.
              </p>
              <button
                onClick={google}
                disabled={authBusy}
                className="mt-6 flex w-full items-center justify-center gap-3 rounded-xl border border-line bg-white px-5 py-3 text-sm font-medium text-[#1f1f1f] shadow-[0_10px_26px_-12px_rgba(74,62,34,0.4)] transition-transform hover:-translate-y-0.5 disabled:opacity-60"
              >
                <GoogleG /> {authBusy ? "Opening Google…" : "Continue with Google"}
              </button>
              {error && (
                <p className="mt-3 rounded-lg border border-amber/40 p-3 font-mono text-xs text-amber">
                  {error}
                </p>
              )}
              {!firebaseEnabled && (
                <p className="mt-4 text-center font-mono text-[10px] leading-relaxed text-faint">
                  demo mode — Firebase keys not configured, sign-in is skipped
                  <br />
                  (see frontend/.env.local.example)
                </p>
              )}
              {memoryReady && (
                <button
                  onClick={() => router.push("/studio")}
                  className="mt-4 w-full text-center font-mono text-[11px] text-accent underline decoration-dotted underline-offset-4"
                >
                  Memory already built → open Studio
                </button>
              )}
            </motion.div>
          )}

          {step === "consent" && (
            <motion.div key="consent" {...slide}>
              <div className="flex items-center gap-3">
                {profile?.photo ? (
                  <img
                    src={profile.photo}
                    alt=""
                    referrerPolicy="no-referrer"
                    className="h-9 w-9 rounded-full border border-line"
                  />
                ) : (
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent">
                    {profile?.name?.[0] ?? "C"}
                  </span>
                )}
                <div>
                  <p className="text-sm font-medium leading-tight">{profile?.name}</p>
                  <p className="font-mono text-[11px] text-faint">{profile?.email}</p>
                </div>
              </div>

              <p className="label mt-6">the memory will read</p>
              <ul className="mt-3 space-y-2.5">
                {READS.map((s) => (
                  <li key={s.text} className="flex items-start gap-3 text-sm">
                    <span
                      className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] ${
                        s.on
                          ? "border-accent bg-accent text-[#f7fbef]"
                          : "border-line text-faint"
                      }`}
                    >
                      {s.on ? "✓" : ""}
                    </span>
                    <span className={s.on ? "text-fg/90" : "text-faint"}>
                      {s.text}
                      {s.soon && (
                        <span className="ml-2 rounded bg-raised-2 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-amber">
                          soon
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs leading-relaxed text-faint">
                Read-only, public data. Sprout never posts, edits or deletes
                anything on your channel.
              </p>
              <div className="mt-6 flex justify-end gap-2">
                <button onClick={() => setStep("start")} className="btn-ghost px-4 py-2 text-sm">
                  Back
                </button>
                <button onClick={connectYouTube} className="btn-primary px-5 py-2 text-sm">
                  Connect YouTube →
                </button>
              </div>
            </motion.div>
          )}

          {step === "channel" && (
            <motion.div key="channel" {...slide}>
              <p className="label">last step</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight">Your channel</h2>

              {previewTier === "empty" && (
                <>
                  <p className="mt-3 text-sm leading-relaxed text-dim">
                    Your channel is brand new — no uploads yet. That&apos;s okay. Tell Sprout
                    what you&apos;re making so it can pull what&apos;s converting in your niche
                    instead of guessing.
                  </p>
                  <label className="mt-4 block text-xs font-medium text-dim">
                    What&apos;s this channel about?
                  </label>
                  <textarea
                    value={nicheInput}
                    onChange={(e) => setNicheInput(e.target.value)}
                    placeholder="e.g. slow-living vlogs and honest self-improvement essays for people in their 20s"
                    rows={3}
                    className="mt-1.5 w-full resize-none rounded-xl border border-line bg-white/60 px-3 py-2.5 text-sm leading-relaxed outline-none focus:border-accent"
                  />
                </>
              )}

              {previewTier === "warming" && (
                <p className="mt-3 text-sm leading-relaxed text-dim">
                  {videoCount != null ? (
                    <>
                      You have <strong className="font-medium text-fg">{videoCount}</strong> public
                      video{videoCount === 1 ? "" : "s"} — not enough yet for Sprout to trust your
                      personal patterns. It&apos;ll lean on niche trends and competitors for now,
                      and get sharper every time you post.
                    </>
                  ) : (
                    <>
                      Your catalog is still small — Sprout will start with niche trends and
                      competitors until you have enough uploads for personal patterns.
                    </>
                  )}
                </p>
              )}

              {previewTier === "established" && (
                <p className="mt-1.5 text-sm leading-relaxed text-dim">
                  We use your signed-in Google account — no handle typing, no impersonation.
                  {videoCount != null && videoCount >= 10 && (
                    <span className="mt-1 block text-faint">
                      {videoCount} videos detected — full pattern memory ready.
                    </span>
                  )}
                </p>
              )}

              {error && (
                <p className="mt-3 rounded-lg border border-amber/40 p-3 font-mono text-xs text-amber">
                  {error}
                </p>
              )}
              <button
                onClick={previewTier === "empty" ? saveNicheAndBuild : startBuild}
                className="btn-primary mt-6 w-full py-2.5 text-sm"
              >
                Build my memory →
              </button>
              <p className="mt-3 text-center font-mono text-[10px] text-faint">
                ~2–5 min — every fetch is cached
                <br />
                <button
                  onClick={() => router.push("/studio")}
                  className="underline decoration-dotted underline-offset-2 hover:text-accent"
                >
                  explore the live demo instead →
                </button>
              </p>
            </motion.div>
          )}

          {step === "building" && (
            <motion.div key="building" {...slide}>
              {channel && (
                <div className="flex items-center gap-3">
                  {channel.avatar && (
                    <img
                      src={channel.avatar}
                      alt={channel.title}
                      referrerPolicy="no-referrer"
                      className="h-12 w-12 rounded-full border border-line"
                    />
                  )}
                  <div>
                    <p className="text-xl font-semibold leading-none tracking-tight">
                      {channel.title}
                    </p>
                    <p className="mt-1 font-mono text-[11px] text-dim">
                      {Math.round(channel.subscribers / 1000)}k subscribers · {elapsed}s
                    </p>
                  </div>
                </div>
              )}
              <ol className="mt-6 space-y-3">
                {BUILD_STAGES.map((s, i) => (
                  <li key={s.key} className="flex items-center gap-3 font-mono text-sm">
                    <span
                      className={`flex h-5 w-5 items-center justify-center border text-[10px] ${
                        at > i || stage === "done"
                          ? "border-accent bg-accent text-[#f7fbef]"
                          : at === i
                            ? "thinking-dot border-accent text-accent"
                            : "border-line text-faint"
                      }`}
                    >
                      {at > i || stage === "done" ? "✓" : "●"}
                    </span>
                    <span className={at >= i ? "text-fg" : "text-faint"}>{s.label}</span>
                  </li>
                ))}
              </ol>
              <p className="mt-4 min-h-4 truncate font-mono text-[11px] text-dim">{detail}</p>
              {stage === "done" && useBacktestReveal && (
                <p className="stamp-slam label mt-4 inline-block rounded-lg border border-accent/50 px-3 py-1.5 text-accent">
                  memory built — opening studio
                </p>
              )}
            </motion.div>
          )}

          {step === "reveal" && (
            <motion.div key="reveal" {...slide}>
              <p className="label">getting started</p>
              <h2 className="mt-2 text-xl font-semibold tracking-tight">
                Your garden is planted
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-dim">
                {genreSummary ||
                  "Sprout is watching your niche. Post your first videos — every upload teaches it more about you."}
              </p>
              {declaredNiche && (
                <p className="mt-3 rounded-lg border border-line bg-raised/40 px-3 py-2 font-mono text-[11px] text-dim">
                  Niche: {declaredNiche}
                </p>
              )}
              <p className="mt-4 text-sm leading-relaxed text-dim">
                Open the studio for trend-based concept cards and competitor signals. Once you
                have ~10 videos, Sprout automatically switches to pattern-based suggestions —
                no re-onboarding needed.
              </p>
              <div className="mt-5">
                <ConnectTelegram />
              </div>
              <button
                onClick={() => router.push("/studio")}
                className="btn-primary mt-6 w-full py-2.5 text-sm"
              >
                Open my studio →
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}

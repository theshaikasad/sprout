"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type LinkInfo = {
  url: string;
  start_command: string;
  token: string;
  bot_username: string;
};

export default function ConnectTelegram({ compact = false }: { compact?: boolean }) {
  const [linked, setLinked] = useState<boolean | null>(null);
  const [masked, setMasked] = useState("");
  const [link, setLink] = useState<LinkInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<"url" | "cmd" | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await api.telegramStatus();
      setLinked(s.linked);
      setMasked(s.chat_id_masked);
    } catch {
      setLinked(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  async function connect() {
    setError("");
    setBusy(true);
    try {
      const info = await api.telegramLink();
      setLink(info);
    } catch (e) {
      setError(e instanceof Error ? e.message : "couldn't generate link");
    } finally {
      setBusy(false);
    }
  }

  async function copy(text: string, which: "url" | "cmd") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setError("copy failed — select the text manually");
    }
  }

  if (linked) {
    return (
      <div className={compact ? "text-sm" : "panel border-accent/30 bg-accent-soft/20 p-4"}>
        <p className="font-medium text-accent">Telegram connected {masked && `(${masked})`}</p>
        <p className="mt-1 text-xs leading-relaxed text-dim">
          Sprout can nudge you here — drop a one-line idea anytime and it lands in your seed tray.
        </p>
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-3" : "panel border-line p-4"}>
      <div>
        <p className="label">ambient companion</p>
        <h3 className="mt-1 text-base font-semibold tracking-tight">Connect Telegram</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-dim">
          Good news and quick-capture — without opening Studio. One tap links your chat to this account.
        </p>
      </div>

      {!link ? (
        <button
          onClick={connect}
          disabled={busy}
          className="btn-primary w-full py-2.5 text-sm disabled:opacity-60"
        >
          {busy ? "Generating link…" : "Connect Telegram →"}
        </button>
      ) : (
        <div className="space-y-3">
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex w-full items-center justify-center gap-2 py-2.5 text-sm"
          >
            Open @{link.bot_username} in Telegram
          </a>
          <div className="rounded-xl border border-line bg-raised/60 p-3">
            <p className="label !text-[9px]">or paste this into the bot</p>
            <code className="mt-1 block break-all font-mono text-[11px] text-fg">
              {link.start_command}
            </code>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => copy(link.url, "url")}
                className="btn-ghost px-3 py-1.5 text-xs"
              >
                {copied === "url" ? "Copied!" : "Copy link"}
              </button>
              <button
                type="button"
                onClick={() => copy(link.start_command, "cmd")}
                className="btn-ghost px-3 py-1.5 text-xs"
              >
                {copied === "cmd" ? "Copied!" : "Copy /start command"}
              </button>
            </div>
          </div>
          <p className="font-mono text-[10px] text-faint">
            Link expires in 15 minutes — tap again if it goes stale.
          </p>
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-amber/40 p-2 font-mono text-xs text-amber">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={refreshStatus}
        className="font-mono text-[10px] text-accent underline decoration-dotted underline-offset-2"
      >
        already linked? refresh status
      </button>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { touchesGraph } from "@/lib/graphTools";

type Msg = {
  role: "user" | "assistant";
  content: string;
  tools?: string[];
  graphQuery?: boolean;
};

export default function ChatDock({
  onGraphQueryStart,
  onGraphQueryEnd,
  seedMessage,
  onSeedConsumed,
}: {
  onGraphQueryStart?: () => void;
  onGraphQueryEnd?: (tools: string[]) => void;
  /** Prefill the input — e.g. when user taps "Pitch an idea" */
  seedMessage?: string | null;
  onSeedConsumed?: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!seedMessage) return;
    setInput(seedMessage);
    onSeedConsumed?.();
    inputRef.current?.focus();
  }, [seedMessage, onSeedConsumed]);

  async function send(textOverride?: string) {
    const text = (textOverride ?? input).trim();
    if (!text || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    onGraphQueryStart?.();
    try {
      const history = msgs.map(({ role, content }) => ({ role, content }));
      const res = await api.chat(text, history);
      const toolNames = res.tool_calls.map((t) => t.tool);
      const usedGraph = touchesGraph(toolNames);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content: res.reply,
          tools: res.tool_calls.map(
            (t) => `${t.tool}(${Object.values(t.args).join(", ").slice(0, 60)})`,
          ),
          graphQuery: usedGraph,
        },
      ]);
      onGraphQueryEnd?.(toolNames);
    } catch {
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: "Agent unreachable — is the API running?" },
      ]);
      onGraphQueryEnd?.([]);
    } finally {
      setBusy(false);
      setTimeout(() => listRef.current?.scrollTo({ top: 99999, behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-baseline justify-between border-b border-line pb-2">
        <h2 className="serif-accent text-[15px]">Sprout</h2>
        <span className="label" style={{ fontSize: "9px" }}>
          agent · tools over the memory
        </span>
      </div>

      <div ref={listRef} className="mt-2 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {msgs.length === 0 && (
          <p className="text-sm italic leading-relaxed text-faint">
            “How are my last uploads doing?” · “What&apos;s overperforming in my
            niche?” · “Which of my hooks actually hold people?” · “Is the morning-routine
            wave worth riding?” · “Plan the best one for Saturday”
          </p>
        )}
        {msgs.map((m, i) => (
          <div key={i}>
            {m.role === "user" ? (
              <p className="text-sm">
                <span className="font-mono text-[10px] text-accent">you ▸ </span>
                {m.content}
              </p>
            ) : (
              <div>
                {m.tools?.map((t, j) => (
                  <p key={j} className="font-mono text-[10px] text-blue">
                    ⚙ {t}
                  </p>
                ))}
                {m.graphQuery && (
                  <p className="mb-1 font-mono text-[10px] text-accent">
                    ⛁ queried your memory graph
                  </p>
                )}
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg/90">
                  {m.content}
                </p>
              </div>
            )}
          </div>
        ))}
        {busy && (
          <p className="font-mono text-xs text-accent">
            <span className="thinking-dot">●</span>
            <span className="ml-2">querying your memory graph…</span>
          </p>
        )}
      </div>

      <div className="mt-2 shrink-0 flex gap-2 rounded-lg border border-line bg-raised-2 p-1">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask or pitch anything…"
          className="flex-1 bg-transparent px-2.5 py-1.5 text-sm outline-none placeholder:text-faint"
        />
        <button
          onClick={() => send()}
          disabled={busy}
          className="btn-primary px-4 text-xs disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}

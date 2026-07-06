"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { GraphData, GraphNode, Trace } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

/* gouache palette on cream paper — ink labels, clay = you, moss = trends */
const INK = "#3a3f2c";
const YOU = "#b45f35";
const ACCENT = "#47702f";
const BLUE = "#3e6f8c";
const AMBER = "#96611e";
const TOPIC = "#75704d";
const HOOK = "#8f6fae";

type FGNode = GraphNode & { x?: number; y?: number; fx?: number; fy?: number };
type FGLink = { source: string | FGNode; target: string | FGNode; rel: string };

function nodeColor(n: GraphNode): string {
  if (n.type === "Trend") return ACCENT;
  if (n.type === "Topic") return TOPIC;
  if (n.type === "Format") return AMBER;
  if (n.type === "Hook") return HOOK;
  if (n.node_sets.includes("my_channel")) return YOU;
  if (n.node_sets.includes("competitors")) return BLUE;
  if (n.node_sets.includes("trends")) return ACCENT;
  return TOPIC;
}

function nodeRadius(n: GraphNode): number {
  switch (n.type) {
    case "Trend": return 5;
    case "Creator": return 4;
    case "Format": return 4;
    case "Video": return n.views ? Math.min(6, 2 + Math.log10(n.views + 1) * 0.6) : 2.5;
    case "Topic": return 2.2;
    default: return 1.4;
  }
}

/** hop order for the traversal animation: trend → topics → videos → formats+hooks */
function hopOf(id: string, trace: Trace): number | null {
  if (trace.trend && id === trace.trend) return 0;
  if (trace.topics.includes(id)) return 1;
  if (trace.videos.includes(id)) return 2;
  if (trace.formats.includes(id) || trace.hooks.includes(id)) return 3;
  return null;
}

function traceKey(trace: Trace): string {
  return JSON.stringify([
    trace.trend,
    trace.topics,
    trace.videos,
    trace.formats,
    trace.hooks,
  ]);
}

const HOP_MS = 650;

function pinNodes(nodes: FGNode[]) {
  for (const n of nodes) {
    if (n.x !== undefined && n.y !== undefined) {
      n.fx = n.x;
      n.fy = n.y;
    }
  }
}

function unpinNodes(nodes: FGNode[]) {
  for (const n of nodes) {
    n.fx = undefined;
    n.fy = undefined;
  }
}

export default function GraphPanel({
  graph,
  trace,
  querying = false,
}: {
  graph: GraphData | null;
  trace: Trace | null;
  querying?: boolean;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [size, setSize] = useState({ w: 480, h: 420 });
  const traceStart = useRef<number>(0);
  const zoomTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const refreshRaf = useRef<number | null>(null);
  const initialFitDone = useRef(false);
  const lastAnimatedTrace = useRef<string | null>(null);
  const lastGraphSig = useRef("");

  function graphSig(g: GraphData | null): string {
    if (!g) return "";
    return `${g.nodes.length}:${g.edges.length}:${g.nodes[0]?.id ?? ""}`;
  }

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    if (!graph) return { nodes: [], links: [] };
    return {
      nodes: graph.nodes.map((n) => ({ ...n })) as FGNode[],
      links: graph.edges.map((e) => ({ ...e })) as FGLink[],
    };
  }, [graph]);

  const dataRef = useRef(data);
  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  const traceNodeIds = useMemo(() => {
    if (!trace) return null;
    return new Set(
      [trace.trend, ...trace.topics, ...trace.videos, ...trace.formats, ...trace.hooks].filter(
        Boolean,
      ) as string[],
    );
  }, [trace]);

  const clearZoomTimers = useCallback(() => {
    zoomTimers.current.forEach(clearTimeout);
    zoomTimers.current = [];
  }, []);

  const stopRefreshLoop = useCallback(() => {
    if (refreshRaf.current !== null) {
      cancelAnimationFrame(refreshRaf.current);
      refreshRaf.current = null;
    }
  }, []);

  const startRefreshLoop = useCallback(
    (durationMs: number) => {
      stopRefreshLoop();
      const start = performance.now();
      const tick = () => {
        fgRef.current?.refresh?.();
        if (performance.now() - start < durationMs) {
          refreshRaf.current = requestAnimationFrame(tick);
        } else {
          refreshRaf.current = null;
        }
      };
      refreshRaf.current = requestAnimationFrame(tick);
    },
    [stopRefreshLoop],
  );

  useEffect(() => () => {
    clearZoomTimers();
    stopRefreshLoop();
  }, [clearZoomTimers, stopRefreshLoop]);

  /* Freeze layout once settled; fit camera once on first load. */
  const handleEngineStop = useCallback(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const nodes = dataRef.current.nodes;
    pinNodes(nodes);

    if (!initialFitDone.current && !trace && !querying) {
      fg.zoomToFit(400, 40);
      initialFitDone.current = true;
    }
  }, [trace, querying]);

  /* New graph payload → one layout pass, then freeze via onEngineStop. */
  useEffect(() => {
    const sig = graphSig(graph);
    if (sig === lastGraphSig.current) return;
    lastGraphSig.current = sig;

    initialFitDone.current = false;
    lastAnimatedTrace.current = null;
    const fg = fgRef.current;
    if (!fg) return;
    unpinNodes(data.nodes);
    fg.d3ReheatSimulation?.();
  }, [graph, data]);

  /* Clear animation lock when a new query starts so re-runs can replay the path. */
  useEffect(() => {
    if (querying) lastAnimatedTrace.current = null;
  }, [querying]);

  /* Retrieval camera: only when a new trace arrives after querying finishes. */
  useEffect(() => {
    clearZoomTimers();
    if (querying || !trace) {
      if (!trace) lastAnimatedTrace.current = null;
      return;
    }

    const key = traceKey(trace);
    if (key === lastAnimatedTrace.current) return;

    const fg = fgRef.current;
    if (!fg) return;

    const runCamera = () => {
      lastAnimatedTrace.current = key;
      traceStart.current = performance.now();

      const nodes = dataRef.current.nodes;
      const byId = new Map(nodes.map((n) => [n.id, n]));
      const hops: string[][] = [
        trace.trend ? [trace.trend] : [],
        trace.topics,
        trace.videos,
        [...trace.formats, ...trace.hooks],
      ].filter((h) => h.length > 0);

      const animMs = hops.length * HOP_MS + 1000;
      startRefreshLoop(animMs);

      hops.forEach((ids, i) => {
        zoomTimers.current.push(
          setTimeout(() => {
            const pts = ids
              .map((nid) => byId.get(nid))
              .filter((n) => n?.x !== undefined) as FGNode[];
            if (!pts.length) return;
            const cx = pts.reduce((s, n) => s + n.x!, 0) / pts.length;
            const cy = pts.reduce((s, n) => s + n.y!, 0) / pts.length;
            fg.centerAt(cx, cy, 550);
            fg.zoom(3.2, 550);
          }, i * HOP_MS),
        );
      });

      zoomTimers.current.push(
        setTimeout(
          () =>
            fg.zoomToFit(
              700,
              60,
              (n: FGNode) =>
                new Set(
                  [trace.trend, ...trace.topics, ...trace.videos, ...trace.formats, ...trace.hooks]
                    .filter(Boolean) as string[],
                ).has(n.id),
            ),
          hops.length * HOP_MS + 250,
        ),
      );
    };

    const waitForPositions = (attempt = 0) => {
      const nodes = dataRef.current.nodes;
      const ids = [
        trace.trend,
        ...trace.topics,
        ...trace.videos,
        ...trace.formats,
        ...trace.hooks,
      ].filter(Boolean) as string[];
      const ready =
        ids.length === 0 ||
        ids.every((id) => {
          const n = nodes.find((node) => node.id === id);
          return n?.x !== undefined && n?.y !== undefined;
        });
      if (ready || attempt > 30) {
        runCamera();
        return;
      }
      zoomTimers.current.push(setTimeout(() => waitForPositions(attempt + 1), 80));
    };

    waitForPositions();
    return clearZoomTimers;
  }, [trace, querying, clearZoomTimers, startRefreshLoop]);

  const id = (v: string | FGNode) => (typeof v === "string" ? v : v.id);
  const elapsed = () => performance.now() - traceStart.current;

  return (
    <div ref={wrapRef} className="relative h-full w-full">
      {querying && (
        <div className="pointer-events-none absolute inset-x-0 top-2 z-20 flex justify-center">
          <span className="rounded-full border border-accent/40 bg-raised/95 px-3 py-1 font-mono text-[10px] text-accent shadow-sm backdrop-blur">
            <span className="thinking-dot">●</span> querying your memory graph…
          </span>
        </div>
      )}
      <ForceGraph2D
        ref={fgRef}
        width={size.w}
        height={size.h}
        graphData={data}
        backgroundColor="rgba(0,0,0,0)"
        cooldownTicks={80}
        warmupTicks={0}
        enableNodeDrag={false}
        autoPauseRedraw
        onEngineStop={handleEngineStop}
        nodeRelSize={1}
        linkColor={(link) => {
          const l = link as unknown as FGLink;
          if (!traceNodeIds || querying) return "rgba(58,63,44,0.14)";
          const on = traceNodeIds.has(id(l.source)) && traceNodeIds.has(id(l.target));
          return on ? ACCENT : "rgba(58,63,44,0.05)";
        }}
        linkWidth={(link) => {
          const l = link as unknown as FGLink;
          return traceNodeIds &&
            !querying &&
            traceNodeIds.has(id(l.source)) &&
            traceNodeIds.has(id(l.target))
            ? 1.8
            : 0.4;
        }}
        nodeCanvasObject={(obj, ctx: CanvasRenderingContext2D, scale: number) => {
          const node = obj as unknown as FGNode;
          const r = nodeRadius(node);
          const hop = trace && !querying ? hopOf(node.id, trace) : null;
          const ms = elapsed();
          const lit = hop !== null && ms > hop * HOP_MS;
          const dimmed = trace !== null && !querying && !lit;

          ctx.globalAlpha = dimmed ? 0.12 : 1;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, lit ? r * 1.7 : r, 0, 2 * Math.PI);
          ctx.fillStyle = nodeColor(node);
          ctx.fill();

          if (lit) {
            ctx.strokeStyle = ACCENT;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.arc(node.x!, node.y!, r * 1.7 + 2.5, 0, 2 * Math.PI);
            ctx.stroke();
          }

          if ((lit || !trace || querying) && scale > 0.55) {
            const showLabel =
              lit || querying || !trace || node.type === "Trend" || node.type === "Creator";
            if (showLabel) {
              const label = node.label.length > 34 ? node.label.slice(0, 32) + "…" : node.label;
              ctx.font = `500 ${Math.max(3.4, 10 / scale)}px var(--font-jetbrains), monospace`;
              ctx.fillStyle = INK;
              ctx.textAlign = "center";
              ctx.fillText(label, node.x!, node.y! - r * 1.7 - 3);
            }
          }
          ctx.globalAlpha = 1;
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D) => {
          if (!trace?.trend || querying) return;
          if (elapsed() < HOP_MS) return;
          const nodes = dataRef.current.nodes;
          const byId = new Map(nodes.map((n) => [n.id, n]));
          const t = byId.get(trace.trend);
          if (!t?.x) return;
          ctx.save();
          ctx.setLineDash([3, 3]);
          ctx.strokeStyle = ACCENT;
          ctx.lineWidth = 1.2;
          for (const topicId of trace.topics) {
            const tp = byId.get(topicId);
            if (!tp?.x) continue;
            ctx.beginPath();
            ctx.moveTo(t.x!, t.y!);
            ctx.lineTo(tp.x!, tp.y!);
            ctx.stroke();
          }
          ctx.restore();
        }}
      />
      <div className="pointer-events-none absolute bottom-2 left-3 z-10 font-mono text-[10px] text-dim">
        <span style={{ color: YOU }}>●</span> you&nbsp;&nbsp;
        <span style={{ color: BLUE }}>●</span> competitors&nbsp;&nbsp;
        <span style={{ color: ACCENT }}>●</span> trends&nbsp;&nbsp;
        <span style={{ color: TOPIC }}>●</span> topics&nbsp;&nbsp;
        <span style={{ color: AMBER }}>●</span> formats
        {trace && !querying && (
          <span className="ml-3" style={{ color: ACCENT }}>
            — — semantic hop
          </span>
        )}
      </div>
    </div>
  );
}

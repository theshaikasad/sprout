"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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

type FGNode = GraphNode & { x?: number; y?: number };
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

const HOP_MS = 650;

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

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    if (!graph) return { nodes: [], links: [] };
    return {
      nodes: graph.nodes as FGNode[],
      links: graph.edges.map((e) => ({ ...e })) as FGLink[],
    };
  }, [graph]);

  const traceNodeIds = useMemo(() => {
    if (!trace) return null;
    return new Set(
      [trace.trend, ...trace.topics, ...trace.videos, ...trace.formats, ...trace.hooks].filter(
        Boolean,
      ) as string[],
    );
  }, [trace]);

  /* THE RETRIEVAL CAMERA: fly to each hop as the query walks the graph,
     then pull back to frame the whole path. */
  useEffect(() => {
    traceStart.current = performance.now();
    zoomTimers.current.forEach(clearTimeout);
    zoomTimers.current = [];
    const fg = fgRef.current;
    if (!fg || !trace) return;

    const byId = new Map((data.nodes as FGNode[]).map((n) => [n.id, n]));
    const hops: string[][] = [
      trace.trend ? [trace.trend] : [],
      trace.topics,
      trace.videos,
      [...trace.formats, ...trace.hooks],
    ].filter((h) => h.length > 0);

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
    // pull back: frame the full retrieved path
    zoomTimers.current.push(
      setTimeout(
        () => fg.zoomToFit(700, 60, (n: FGNode) => traceNodeIds?.has(n.id) ?? false),
        hops.length * HOP_MS + 250,
      ),
    );
    return () => zoomTimers.current.forEach(clearTimeout);
  }, [trace, data, traceNodeIds]);

  const id = (v: string | FGNode) => (typeof v === "string" ? v : v.id);

  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (!querying) return;
    setPulse(true);
    const t = setInterval(() => setPulse((p) => !p), 700);
    return () => {
      clearInterval(t);
      setPulse(false);
    };
  }, [querying]);

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
        cooldownTicks={180}
        onEngineStop={() => {
          if (!trace) fgRef.current?.zoomToFit(600, 30);
        }}
        nodeRelSize={1}
        enableNodeDrag={false}
        linkColor={(link) => {
          const l = link as unknown as FGLink;
          if (!traceNodeIds) return "rgba(58,63,44,0.14)";
          const on = traceNodeIds.has(id(l.source)) && traceNodeIds.has(id(l.target));
          return on ? ACCENT : "rgba(58,63,44,0.05)";
        }}
        linkWidth={(link) => {
          const l = link as unknown as FGLink;
          return traceNodeIds && traceNodeIds.has(id(l.source)) && traceNodeIds.has(id(l.target))
            ? 1.8
            : 0.4;
        }}
        nodeCanvasObject={(obj, ctx: CanvasRenderingContext2D, scale: number) => {
          const node = obj as unknown as FGNode;
          const r = nodeRadius(node);
          const hop = trace ? hopOf(node.id, trace) : null;
          const elapsed = performance.now() - traceStart.current;
          const lit = hop !== null && elapsed > hop * HOP_MS;
          const dimmed = trace !== null && !lit && !querying;
          const queryPulse = querying && pulse;

          ctx.globalAlpha = dimmed ? 0.09 : queryPulse ? 0.55 + (pulse ? 0.35 : 0.15) : 1;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, lit ? r * 1.7 : r, 0, 2 * Math.PI);
          ctx.fillStyle = nodeColor(node);
          ctx.fill();

          if (lit || queryPulse) {
            ctx.strokeStyle = ACCENT;
            ctx.lineWidth = queryPulse ? 1.2 : 0.8;
            ctx.beginPath();
            ctx.arc(node.x!, node.y!, (lit ? r * 1.7 : r) + 2.5, 0, 2 * Math.PI);
            ctx.stroke();
          }

          if ((lit || queryPulse || (!trace && node.type === "Trend")) && scale > 0.6) {
            const label = node.label.length > 34 ? node.label.slice(0, 32) + "…" : node.label;
            ctx.font = `500 ${Math.max(3.4, 10 / scale)}px var(--font-jetbrains), monospace`;
            ctx.fillStyle = INK;
            ctx.textAlign = "center";
            ctx.fillText(label, node.x!, node.y! - r * 1.7 - 3);
          }
          ctx.globalAlpha = 1;
        }}
        onRenderFramePost={(ctx: CanvasRenderingContext2D) => {
          // the semantic hop (query ~ topic) is a vector edge, not a graph edge —
          // draw it dashed, honestly different from real edges
          if (!trace?.trend) return;
          const elapsed = performance.now() - traceStart.current;
          if (elapsed < HOP_MS) return;
          const byId = new Map((data.nodes as FGNode[]).map((n) => [n.id, n]));
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
        {trace && <span className="ml-3" style={{ color: ACCENT }}>— — semantic hop</span>}
      </div>
    </div>
  );
}

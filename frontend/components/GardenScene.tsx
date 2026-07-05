"use client";

/* One painted cutaway that can render either as a framed card or as a
   full-bleed page background. Sky + tall plant + bloom above the soil line,
   the Cognee memory taking root as labeled nodes below. */

import { useEffect, useId } from "react";
import { animate, motion, useMotionValue, type MotionValue, useTransform } from "motion/react";

const EASE = [0.16, 0.8, 0.3, 1] as const;

type Variant = "card" | "background";

function layout(variant: Variant) {
  if (variant === "background") {
    return {
      W: 1440,
      H: 800,
      CX: 1080,
      SOIL_Y: 500,
      BLOOM_Y: 88,
      VB: "0 0 1440 800",
      par: "xMidYMid slice" as const,
      s: 1.45,
      font: 9,
      nodeR: 4.5,
      spreadX: 0.48,
      leafMul: 0.52,
      rootDepth: 0.62,
      framed: false,
    };
  }
  return {
    W: 280,
    H: 460,
    CX: 140,
    SOIL_Y: 302,
    BLOOM_Y: 40,
    VB: "0 -32 280 492",
    par: "xMidYMid meet" as const,
    s: 1,
    font: 8,
    nodeR: 4,
    spreadX: 1,
    leafMul: 1,
    rootDepth: 1,
    framed: true,
  };
}

/* roots described as fractions of the layout so they scale to any size */
const ROOT_SPECS = [
  { fx: -0.34, fy: 0.48, c: "#e0a53a", label: "hooks", anchor: "end" as const, side: -1, a: 0.2, b: 0.32 },
  { fx: -0.1, fy: 0.58, c: "#cf7c4c", label: "formats", anchor: "end" as const, side: -1, a: 0.28, b: 0.4 },
  { fx: 0.14, fy: 0.52, c: "#6b96f2", label: "topics", anchor: "start" as const, side: 1, a: 0.38, b: 0.5 },
  { fx: 0.38, fy: 0.38, c: "#4e9e6f", label: "trends", anchor: "start" as const, side: 1, a: 0.48, b: 0.6 },
  { fx: -0.52, fy: 0.6, c: "#a06bd6", label: "rivals", anchor: "end" as const, side: -1, a: 0.58, b: 0.7 },
];

function rootGeometry(L: ReturnType<typeof layout>) {
  const originY = L.SOIL_Y - 6;
  const belowH = L.H - L.SOIL_Y;
  const maxTy = L.SOIL_Y + belowH * L.rootDepth;
  return ROOT_SPECS.map((r) => {
    const tx = L.CX + r.fx * L.W * L.spreadX;
    const ty = Math.min(L.SOIL_Y + r.fy * belowH, maxTy);
    const c1x = L.CX + (tx - L.CX) * 0.22;
    const c1y = originY + (ty - originY) * 0.38;
    const c2x = L.CX + (tx - L.CX) * 0.68;
    const c2y = originY + (ty - originY) * 0.72;
    const d = `M${L.CX} ${originY} C ${c1x} ${c1y} ${c2x} ${c2y} ${tx} ${ty}`;
    const dx = r.side * 9 * L.s;
    return { ...r, tx, ty, d, dx };
  });
}

function GouacheLeaf({
  x, y, size, flip, color, light, scale, opacity, rotate,
}: {
  x: number; y: number; size: number; flip?: boolean; color: string; light: string;
  scale?: MotionValue<number> | number;
  opacity?: MotionValue<number> | number;
  rotate?: MotionValue<number> | number;
}) {
  return (
    <g transform={`translate(${x} ${y})${flip ? " scale(-1 1)" : ""}`}>
      <motion.g style={{ scale, opacity, rotate, transformBox: "fill-box", transformOrigin: "0% 65%" }}>
        <g transform={`scale(${size / 62})`}>
          <path d="M0 2 C 18 -20 52 -14 64 4 C 50 22 14 20 0 2 Z" fill={color} stroke="#3f6a32" strokeWidth="0.8" strokeOpacity="0.25" />
          <path d="M4 4 C 24 6 44 8 58 6" stroke={light} strokeWidth="1.2" strokeOpacity="0.35" fill="none" strokeLinecap="round" />
        </g>
      </motion.g>
    </g>
  );
}

function RootNode({
  x, y, r, color, label, font, scale, opacity, dx = 0, anchor = "middle" as const,
}: {
  x: number; y: number; r: number; color: string; label: string; font: number;
  scale?: MotionValue<number> | number;
  opacity?: MotionValue<number> | number;
  dx?: number;
  anchor?: "start" | "middle" | "end";
}) {
  return (
    <motion.g style={{ opacity }}>
      <motion.circle cx={x} cy={y} r={r} fill={color} style={{ scale, transformBox: "fill-box", transformOrigin: "50% 50%" }} />
      <circle cx={x} cy={y} r={r + r * 0.7} fill="none" stroke={color} strokeWidth={r * 0.28} strokeOpacity="0.45" />
      <text x={x + dx} y={y + font * 0.36} textAnchor={anchor} fill="#f6eedd" style={{ fontFamily: "var(--font-jetbrains), monospace", fontSize: font, letterSpacing: 0.3, paintOrder: "stroke", stroke: "rgba(30,20,10,0.75)", strokeWidth: font * 0.22 }}>
        {label}
      </text>
    </motion.g>
  );
}

export type GardenPlantProps = {
  mode: "hero" | "scroll";
  variant?: Variant;
  progress: MotionValue<number>;
  className?: string;
  caption?: string;
};

export function GardenPlant({ mode, variant = "card", progress, className = "", caption }: GardenPlantProps) {
  const uid = useId().replace(/:/g, "");
  const isHero = mode === "hero";
  const L = layout(variant);
  const { W, H, CX, SOIL_Y, BLOOM_Y, VB, par, s, font, nodeR, framed, leafMul } = L;
  const roots = rootGeometry(L);

  const stemLen = useTransform(progress, [0.06, 0.68], [0, 1], { clamp: true });
  const rootLen = useTransform(progress, [0.08, 0.72], [0.2, 1], { clamp: true });
  const edgeLen = useTransform(progress, [0.62, 0.86], [0, 1], { clamp: true });
  const seedOp = useTransform(progress, [0, 0.1], [1, 0], { clamp: true });
  const budOp = useTransform(progress, [0.55, 0.68, 0.76], [0, 1, 0], { clamp: true });
  const bloom = useTransform(progress, [0.7, 0.92], [0, 1], { clamp: true });
  const canTilt = useTransform(progress, [0, 0.12], [-6, -20]);
  const glow = useTransform(progress, [0, 0.35], [0.15, 0.45], { clamp: true });

  // stem geometry (wavy vertical from soil up to the bloom)
  const s0 = SOIL_Y - 8;
  const top = BLOOM_Y + 10;
  const h = s0 - top;
  const amp = W * 0.03;
  const stemPath = `M${CX} ${s0} C ${CX - amp} ${s0 - h * 0.2} ${CX + amp} ${s0 - h * 0.42} ${CX} ${s0 - h * 0.56} C ${CX - amp} ${s0 - h * 0.72} ${CX + amp} ${s0 - h * 0.9} ${CX} ${top}`;
  const leafSize = W * 0.12 * leafMul;
  const leafYs = [0.2, 0.4, 0.58, 0.74].map((f) => s0 - h * f);

  // scroll edges between a few nodes (semantic bridges in the graph)
  const edgePairs = [[0, 2], [1, 3], [2, 4]];
  const edges = edgePairs.map(([i, j]) => {
    const a = roots[i], b = roots[j];
    return `M${a.tx} ${a.ty} C ${(a.tx + b.tx) / 2} ${a.ty + 14} ${(a.tx + b.tx) / 2} ${b.ty - 14} ${b.tx} ${b.ty}`;
  });

  const frameClass = framed
    ? "rounded-2xl border border-white/55 shadow-[0_8px_36px_-10px_rgba(74,62,34,0.3)]"
    : "";

  return (
    <div className={`relative overflow-hidden ${frameClass} ${className}`}>
      <svg viewBox={VB} className="block h-full w-full" preserveAspectRatio={par} fill="none">
        <defs>
          <linearGradient id={`${uid}-sky`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#cfe6ef" />
            <stop offset="55%" stopColor="#e8f0e2" />
            <stop offset="100%" stopColor="#eddfc4" />
          </linearGradient>
          <linearGradient id={`${uid}-soil`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7a5230" />
            <stop offset="100%" stopColor="#3d2818" />
          </linearGradient>
          <linearGradient id={`${uid}-stem`} x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#3f6a32" />
            <stop offset="100%" stopColor="#8fcf72" />
          </linearGradient>
        </defs>

        {/* sky — bleed past edges so slice never leaves gaps */}
        <rect x={-400} y={-40} width={W + 800} height={SOIL_Y + 40} fill={`url(#${uid}-sky)`} />
        <circle cx={W * 0.8} cy={BLOOM_Y * 0.5 + 10} r={30 * s * 0.55} fill="#ffe9a8" fillOpacity="0.9" />
        <circle cx={W * 0.8} cy={BLOOM_Y * 0.5 + 10} r={19 * s * 0.55} fill="#fff4d6" />
        <ellipse cx={W * 0.16} cy={SOIL_Y * 0.2} rx={34 * s * 0.6} ry={11 * s * 0.6} fill="white" fillOpacity="0.5" />
        <ellipse cx={W * 0.86} cy={SOIL_Y * 0.32} rx={26 * s * 0.6} ry={9 * s * 0.6} fill="white" fillOpacity="0.38" />

        {/* soil — full width bleed */}
        <rect x={-400} y={SOIL_Y} width={W + 800} height={H - SOIL_Y + 60} fill={`url(#${uid}-soil)`} />

        {/* roots */}
        {roots.map((r) => (
          <motion.path key={r.label} d={r.d} stroke="#c9a070" strokeWidth={2.2 * s} strokeLinecap="round" strokeOpacity="0.9" style={{ pathLength: rootLen }} />
        ))}

        {!isHero && edges.map((d, i) => (
          <motion.path key={`e${i}`} d={d} stroke="#e8dcc4" strokeWidth={1 * s} strokeOpacity="0.35" strokeDasharray={`${3 * s} ${4 * s}`} style={{ pathLength: edgeLen }} />
        ))}

        {roots.map((r, i) => (
          <NodeAppear key={r.label} x={r.tx} y={r.ty} r={nodeR} color={r.c} label={r.label} font={font} dx={r.dx} anchor={r.anchor} progress={progress} a={r.a} b={r.b} auto={isHero} index={i} />
        ))}

        <motion.ellipse cx={CX} cy={SOIL_Y + 1} rx={50 * s} ry={9 * s} fill="#5d8a45" style={{ opacity: glow }} />

        {!isHero && (
          <motion.g style={{ opacity: seedOp }}>
            <ellipse cx={CX} cy={SOIL_Y - 8} rx={7 * s * 0.7} ry={8 * s * 0.7} fill="#a9743f" />
          </motion.g>
        )}

        {/* plant */}
        <motion.g
          animate={isHero ? { rotate: [-1.2, 1.2, -1.2] } : undefined}
          transition={isHero ? { duration: 7, repeat: Infinity, ease: "easeInOut" } : undefined}
          style={{ transformOrigin: `${CX}px ${SOIL_Y}px` }}
        >
          <motion.path d={stemPath} stroke={`url(#${uid}-stem)`} strokeWidth={5.5 * s} strokeLinecap="round" style={{ pathLength: stemLen }} />

          <Leaf progress={progress} a={0.16} b={0.28} x={CX} y={leafYs[0]} size={leafSize} />
          <Leaf progress={progress} a={0.16} b={0.28} x={CX} y={leafYs[0] + 2} size={leafSize * 0.92} flip />
          <Leaf progress={progress} a={0.3} b={0.44} x={CX} y={leafYs[1]} size={leafSize * 1.12} />
          <Leaf progress={progress} a={0.3} b={0.44} x={CX} y={leafYs[1] + 2} size={leafSize} flip />
          <Leaf progress={progress} a={0.44} b={0.58} x={CX} y={leafYs[2]} size={leafSize * 1.05} />
          <Leaf progress={progress} a={0.44} b={0.58} x={CX} y={leafYs[2] + 2} size={leafSize * 0.95} flip />
          <Leaf progress={progress} a={0.56} b={0.68} x={CX} y={leafYs[3]} size={leafSize * 0.9} />
          <Leaf progress={progress} a={0.56} b={0.68} x={CX} y={leafYs[3] + 2} size={leafSize * 0.82} flip />

          {!isHero && (
            <motion.g style={{ opacity: budOp }}>
              <path d={`M${CX} ${top + 22 * s} C ${CX - 8 * s} ${top + 10 * s} ${CX - 8 * s} ${top} ${CX} ${top - 8 * s} C ${CX + 8 * s} ${top} ${CX + 8 * s} ${top + 10 * s} ${CX} ${top + 22 * s} Z`} fill="#5d8a45" />
            </motion.g>
          )}

          {isHero ? (
            <AutoBloom cx={CX} cy={BLOOM_Y} s={s} progress={progress} />
          ) : (
            <g transform={`translate(${CX} ${BLOOM_Y})`}>
              <motion.g style={{ scale: bloom, opacity: bloom, transformBox: "fill-box", transformOrigin: "50% 100%" }}>
                <BloomPetals s={s} />
              </motion.g>
            </g>
          )}
        </motion.g>

        {/* pot rim + grass */}
        <ellipse cx={CX} cy={SOIL_Y + 2} rx={46 * s} ry={10 * s} fill="none" stroke="#5a3d22" strokeWidth={1.4 * s} strokeOpacity="0.7" />
        {[[-32, -4, -12], [34, -2, 10], [12, -8, -8]].map(([ox, oy, t], i) => (
          <path key={i} d={`M${CX + (ox as number) * s} ${SOIL_Y + (oy as number)} q ${(t as number) * s} ${-12 * s} ${(t as number) * 0.35 * s} ${-18 * s}`} stroke="#6f9a52" strokeWidth={2 * s} strokeLinecap="round" />
        ))}

        {!isHero && (
          <>
            <motion.g style={{ rotate: canTilt, transformOrigin: `${CX + 70 * s}px ${SOIL_Y - 100 * s}px` }}>
              <g transform={`translate(${CX + 40 * s} ${BLOOM_Y + 20 * s}) scale(${s})`}>
                <path d="M8 6 h34 a4 4 0 0 1 4 4 v16 a8 8 0 0 1 -8 8 h-22 a8 8 0 0 1 -8 -8 v-16 a4 4 0 0 1 4 -4 z" fill="#6a9eb5" stroke="#3d6278" strokeWidth="1" />
                <path d="M8 22 L-20 12 L-22 24 L8 34 Z" fill="#8ec0d8" stroke="#3d6278" strokeWidth="1" />
                <ellipse cx="-24" cy="18" rx="4" ry="7" fill="#5a8fa8" />
                <path d="M10 8 q11 -14 24 -2" stroke="#3d6278" strokeWidth="2" fill="none" strokeLinecap="round" />
              </g>
            </motion.g>
            {[0, 0.45, 0.9].map((delay, i) => (
              <motion.ellipse
                key={i}
                cx={CX + (i - 1) * 3 * s}
                cy={0}
                rx={2 * s}
                ry={4 * s}
                fill="#8ec0d8"
                initial={{ y: BLOOM_Y + 40 * s, opacity: 0 }}
                animate={{ y: [BLOOM_Y + 40 * s, SOIL_Y - 12], opacity: [0, 0.85, 0] }}
                transition={{ duration: 1.4, delay, repeat: Infinity, ease: "easeIn", times: [0, 0.15, 1] }}
              />
            ))}
          </>
        )}
      </svg>

      {caption && framed && (
        <span className="absolute bottom-2 left-2 right-2 z-[2] rounded-full border border-white/45 bg-black/30 px-3 py-1 text-center text-[9px] text-[#f6eedd] backdrop-blur-sm">
          {caption}
        </span>
      )}
    </div>
  );
}

function BloomPetals({ s }: { s: number }) {
  const rx = 9 * s;
  const ry = 15 * s;
  return (
    <>
      {[0, 60, 120, 180, 240, 300].map((deg) => (
        <ellipse key={deg} cx="0" cy={-ry + 2 * s} rx={rx} ry={ry} fill="#e08aa0" transform={`rotate(${deg})`} />
      ))}
      <circle cx="0" cy="0" r={7 * s} fill="#e6b54b" />
    </>
  );
}

function AutoBloom({ cx, cy, s, progress }: { cx: number; cy: number; s: number; progress: MotionValue<number> }) {
  const scale = useTransform(progress, [0.62, 0.82], [0, 1], { clamp: true });
  const opacity = useTransform(progress, [0.62, 0.72], [0, 1], { clamp: true });
  return (
    <g transform={`translate(${cx} ${cy})`}>
      <motion.g style={{ scale, opacity, transformBox: "fill-box", transformOrigin: "50% 50%" }}>
        <BloomPetals s={s} />
      </motion.g>
    </g>
  );
}

function NodeAppear({
  x, y, r, color, label, font, dx, anchor, progress, a, b, auto, index,
}: {
  x: number; y: number; r: number; color: string; label: string; font: number;
  dx: number; anchor: "start" | "middle" | "end";
  progress: MotionValue<number>; a: number; b: number; auto: boolean; index: number;
}) {
  const start = auto ? 0.32 + index * 0.1 : a;
  const end = auto ? start + 0.12 : b;
  const scale = useTransform(progress, [start, end], [0, 1], { clamp: true });
  const opacity = useTransform(progress, [start, start + 0.05], [0, 1], { clamp: true });
  return <RootNode x={x} y={y} r={r} color={color} label={label} font={font} dx={dx} anchor={anchor} scale={scale} opacity={opacity} />;
}

function Leaf({ progress, a, b, x, y, size, flip }: { progress: MotionValue<number>; a: number; b: number; x: number; y: number; size: number; flip?: boolean }) {
  const scale = useTransform(progress, [a, b], [0.08, 1], { clamp: true });
  const opacity = useTransform(progress, [a, (a + b) / 2], [0, 1], { clamp: true });
  const rotate = useTransform(progress, [a, b], [flip ? 28 : -28, 0], { clamp: true });
  return <GouacheLeaf x={x} y={y} size={size} flip={flip} color={flip ? "#6f9a52" : "#7fb06a"} light="#c8e8b0" scale={scale} opacity={opacity} rotate={rotate} />;
}

export function HeroGarden() {
  const progress = useMotionValue(0);
  useEffect(() => {
    const ctrl = animate(progress, 1, { duration: 3.6, ease: EASE });
    return () => ctrl.stop();
  }, [progress]);

  return (
    <GardenPlant
      mode="hero"
      progress={progress}
      className="mx-auto aspect-[3/5] w-full max-w-[300px]"
      caption="🌱 above: your videos · below: the memory taking root"
    />
  );
}

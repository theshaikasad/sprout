"use client";

/* Ambient gouache wash — soft brush blobs drift and breathe so the section
   feels like a hand-painted meadow, not a CSS gradient slab. */

import { useEffect, useRef } from "react";

const PALETTE = [
  { r: 182, g: 214, b: 228, a: 0.55 }, // sky
  { r: 157, g: 191, b: 136, a: 0.5 },  // sage
  { r: 230, g: 181, b: 75, a: 0.38 },  // wheat sun
  { r: 207, g: 124, b: 76, a: 0.32 },  // clay
  { r: 93, g: 138, b: 69, a: 0.28 },   // moss
  { r: 224, g: 138, b: 160, a: 0.22 }, // bloom
  { r: 240, g: 230, b: 208, a: 0.65 }, // cream paper
];

type Blob = {
  x: number;
  y: number;
  r: number;
  color: (typeof PALETTE)[number];
  phaseX: number;
  phaseY: number;
  speed: number;
  drift: number;
};

function makeBlobs(w: number, h: number): Blob[] {
  return PALETTE.map((color, i) => ({
    x: w * (0.15 + (i * 0.13) % 0.7),
    y: h * (0.1 + (i * 0.17) % 0.75),
    r: Math.min(w, h) * (0.28 + (i % 3) * 0.08),
    color,
    phaseX: i * 1.7,
    phaseY: i * 2.3,
    speed: 0.00018 + i * 0.00004,
    drift: 0.00012 + i * 0.00003,
  }));
}

export default function LivingPainting({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reducedRef = useRef(false);

  useEffect(() => {
    reducedRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let blobs: Blob[] = [];
    let t = 0;

    const paint = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(1, Math.floor(rect.width));
      const h = Math.max(1, Math.floor(rect.height));
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        blobs = makeBlobs(w, h);
      }

      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#f2ead8";
      ctx.fillRect(0, 0, w, h);

      ctx.globalCompositeOperation = "multiply";
      for (const b of blobs) {
        const ox = reducedRef.current ? 0 : Math.sin(t * b.speed + b.phaseX) * w * 0.04;
        const oy = reducedRef.current ? 0 : Math.cos(t * b.drift + b.phaseY) * h * 0.035;
        const pulse = reducedRef.current ? 1 : 1 + Math.sin(t * 0.0008 + b.phaseY) * 0.06;
        const { r, g, b: bl, a } = b.color;
        const grad = ctx.createRadialGradient(b.x + ox, b.y + oy, 0, b.x + ox, b.y + oy, b.r * pulse);
        grad.addColorStop(0, `rgba(${r},${g},${bl},${a})`);
        grad.addColorStop(0.55, `rgba(${r},${g},${bl},${a * 0.45})`);
        grad.addColorStop(1, `rgba(${r},${g},${bl},0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.ellipse(b.x + ox, b.y + oy, b.r * pulse * 1.1, b.r * pulse * 0.85, b.phaseX * 0.1, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 0.035;
      for (let i = 0; i < 120; i++) {
        const nx = (Math.sin(i * 12.9898 + t * 0.0001) * 0.5 + 0.5) * w;
        const ny = (Math.cos(i * 78.233 + t * 0.00008) * 0.5 + 0.5) * h;
        ctx.fillStyle = "#3a3f2c";
        ctx.fillRect(nx, ny, 1.2, 1.2);
      }
      ctx.globalAlpha = 1;

      t += 16;
      raf = requestAnimationFrame(paint);
    };

    paint();
    const ro = new ResizeObserver(() => {
      canvas.width = 0;
    });
    ro.observe(canvas);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    />
  );
}

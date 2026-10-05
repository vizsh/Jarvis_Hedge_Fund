"use client";

import { useEffect, useRef } from "react";

type DotGridProps = {
  gap?: number;
  dotSize?: number;
  baseColor?: string;
  activeColor?: string;
  proximity?: number;
  className?: string;
};

/**
 * ReactBits-style DotGrid — a canvas dot lattice whose dots swell and
 * brighten as the cursor approaches. Listens on window so the canvas itself
 * can stay pointer-events-none.
 */
export default function DotGrid({
  gap = 30,
  dotSize = 1.5,
  baseColor = "rgba(184, 241, 77, 0.16)",
  activeColor = "rgba(215, 255, 138, 0.95)",
  proximity = 150,
  className = "",
}: DotGridProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let dots: { x: number; y: number }[] = [];
    const pointer = { x: -9999, y: -9999 };
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const build = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dots = [];
      for (let y = gap / 2; y < h; y += gap) {
        for (let x = gap / 2; x < w; x += gap) {
          dots.push({ x, y });
        }
      }
    };

    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = e.clientX - rect.left;
      pointer.y = e.clientY - rect.top;
    };
    const onLeave = () => {
      pointer.x = -9999;
      pointer.y = -9999;
    };

    const draw = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;
      ctx.clearRect(0, 0, w, h);
      for (const d of dots) {
        const dist = Math.hypot(d.x - pointer.x, d.y - pointer.y);
        const t = Math.max(0, 1 - dist / proximity);
        const ease = t * t * (3 - 2 * t);
        ctx.beginPath();
        ctx.arc(d.x, d.y, dotSize + ease * dotSize * 1.7, 0, Math.PI * 2);
        ctx.fillStyle = ease > 0.03 ? activeColor : baseColor;
        ctx.globalAlpha = 0.4 + ease * 0.6;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    };

    build();
    draw();
    window.addEventListener("resize", build);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", build);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
    };
  }, [gap, dotSize, baseColor, activeColor, proximity]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`pointer-events-none h-full w-full ${className}`}
    />
  );
}

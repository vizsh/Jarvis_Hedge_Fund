import { useId, useMemo, useRef, useState } from "react";

export interface FanPoint { month: number; p10: number; p50: number; p90: number }

const compact = (v: number) => v >= 1e7 ? `${(v / 1e7).toFixed(v >= 1e8 ? 0 : 1)}Cr` : v >= 1e5 ? `${(v / 1e5).toFixed(v >= 1e6 ? 0 : 1)}L` : v >= 1e3 ? `${Math.round(v / 1e3)}k` : `${Math.round(v)}`;

/** Range-of-outcomes chart. Three layers (the 1-in-10 bad and good cases, and the middle path), a goal line,
 *  and a hover readout that follows the pointer or the arrow keys, so every number on it can be read, not guessed. */
export function FanChart({ points, years, target, fmt, labels }: {
  points: FanPoint[]; years: number; target: number; fmt: (n: number) => string;
  labels: { bad: string; mid: string; good: string; goal: string; year: string };
}) {
  const W = 720, H = 300, L = 46, R = 14, T = 14, B = 28;
  const gid = useId().replace(/:/g, "");
  const box = useRef<SVGSVGElement>(null);
  const [hov, setHov] = useState<number | null>(null);

  const g = useMemo(() => {
    const maxY = Math.max(...points.map((p) => p.p90), target) * 1.08;
    const x = (m: number) => L + (m / (years * 12)) * (W - L - R);
    const y = (v: number) => T + (1 - v / maxY) * (H - T - B);
    const path = (k: "p10" | "p50" | "p90") => points.map((p, i) => `${i ? "L" : "M"}${x(p.month).toFixed(1)},${y(p[k]).toFixed(1)}`).join("");
    const band = points.map((p, i) => `${i ? "L" : "M"}${x(p.month).toFixed(1)},${y(p.p90).toFixed(1)}`).join("") +
      [...points].reverse().map((p) => `L${x(p.month).toFixed(1)},${y(p.p10).toFixed(1)}`).join("") + "Z";
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ v: maxY * f, y: y(maxY * f) }));
    const xt = Array.from({ length: Math.min(years, 6) + 1 }, (_, i) => Math.round((years / Math.min(years, 6)) * i));
    return { x, y, line50: path("p50"), line10: path("p10"), line90: path("p90"), band, ticks, xt, ty: y(target) };
  }, [points, years, target]);

  const onMove = (clientX: number) => {
    const r = box.current?.getBoundingClientRect(); if (!r) return;
    const px = ((clientX - r.left) / r.width) * W;
    const m = Math.max(0, Math.min(years * 12, ((px - L) / (W - L - R)) * years * 12));
    let best = 0, d = Infinity;
    points.forEach((p, i) => { const dd = Math.abs(p.month - m); if (dd < d) { d = dd; best = i; } });
    setHov(best);
  };
  const h = hov !== null ? points[hov] : null;
  const tip = h ? { x: g.x(h.month), left: g.x(h.month) > W * 0.62 } : null;

  return (
    <div className="fan">
      <svg ref={box} viewBox={`0 0 ${W} ${H}`} className="fan-svg" role="img" tabIndex={0}
           aria-label={`${labels.mid} ${fmt(points[points.length - 1].p50)}`}
           onPointerMove={(e) => onMove(e.clientX)} onPointerLeave={() => setHov(null)}
           onKeyDown={(e) => { if (e.key === "ArrowRight") setHov((i) => Math.min(points.length - 1, (i ?? -1) + 1)); if (e.key === "ArrowLeft") setHov((i) => Math.max(0, (i ?? 1) - 1)); }}>
        <defs>
          <linearGradient id={`b${gid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--accent)" stopOpacity=".34" /><stop offset="1" stopColor="var(--accent)" stopOpacity=".04" /></linearGradient>
          <clipPath id={`c${gid}`}><rect x="0" y="0" width={W} height={H} className="fan-reveal" /></clipPath>
        </defs>
        {g.ticks.map((t) => (<g key={t.v}><line x1={L} x2={W - R} y1={t.y} y2={t.y} className="fan-grid" /><text x={L - 8} y={t.y + 4} textAnchor="end" className="fan-axis">{compact(t.v)}</text></g>))}
        {g.xt.map((yr) => <text key={yr} x={g.x(yr * 12)} y={H - 8} textAnchor="middle" className="fan-axis">{yr}{labels.year}</text>)}
        <g clipPath={`url(#c${gid})`}>
          <path d={g.band} fill={`url(#b${gid})`} />
          <path d={g.line90} className="fan-edge" /><path d={g.line10} className="fan-edge" />
          <path d={g.line50} className="fan-mid" />
        </g>
        <line x1={L} x2={W - R} y1={g.ty} y2={g.ty} className="fan-goal" />
        <text x={W - R - 4} y={g.ty - 6} textAnchor="end" className="fan-goal-l">{labels.goal} {compact(target)}</text>
        {h && tip && (<g>
          <line x1={tip.x} x2={tip.x} y1={T} y2={H - B} className="fan-cross" />
          {(["p90", "p50", "p10"] as const).map((k) => <circle key={k} cx={tip.x} cy={g.y(h[k])} r={k === "p50" ? 4.5 : 3.2} className={`fan-dot ${k}`} />)}
        </g>)}
      </svg>
      {h && tip && (
        <div className="fan-tip" style={{ left: `${(tip.x / W) * 100}%`, transform: `translateX(${tip.left ? "calc(-100% - 12px)" : "12px"})` }}>
          <div className="fan-tip-h">{h.month % 12 === 0 ? `${h.month / 12} ${labels.year}` : `${Math.floor(h.month / 12)}${labels.year} ${h.month % 12}m`}</div>
          <div><i className="d g" />{labels.good}<b>{fmt(h.p90)}</b></div>
          <div><i className="d m" />{labels.mid}<b>{fmt(h.p50)}</b></div>
          <div><i className="d b" />{labels.bad}<b>{fmt(h.p10)}</b></div>
        </div>
      )}
    </div>
  );
}

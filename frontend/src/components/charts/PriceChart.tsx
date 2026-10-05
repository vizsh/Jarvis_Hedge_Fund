import { useMemo, useRef, useState } from "react";

import { useLang } from "../../lib/lang";
import { useTheme } from "../../lib/theme";

export interface PriceData {
  kind: "price"; ticker: string; name: string; currency: string; source: "live" | "snapshot"; last_date: string; age_days: number | null; tv: string;
  points: [string, number][]; ma50: (number | null)[]; ma200: (number | null)[]; last: number; first: number; high: number; low: number; change_pct: number;
}
export interface CompareData {
  kind: "compare"; source: "live" | "snapshot"; start: string; last_date: string; tv: string[];
  series: { ticker: string; name: string; points: [string, number][]; change_pct: number }[];
}
export type ChartData = PriceData | CompareData;

const W = 680, H = 270, L = 8, R = 62, T = 14, B = 24;
const RANGES: [string, number][] = [["1M", 21], ["3M", 63], ["6M", 126], ["1Y", 9999]];
const LINES = ["var(--accent)", "var(--violet)", "var(--green)"];

const fmtDate = (d: string, hi: boolean) => new Date(d).toLocaleDateString(hi ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "2-digit" });
const nice = (lo: number, hi: number, n = 4): number[] => {
  const span = hi - lo || 1, raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v);
  return out;
};

function useScale(series: number[][], dates: string[]) {
  return useMemo(() => {
    const all = series.flat().filter((v) => Number.isFinite(v));
    let lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo) * 0.08 || 1;
    lo -= pad; hi += pad;
    const n = dates.length;
    const x = (i: number) => L + (i / Math.max(1, n - 1)) * (W - L - R);
    const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    return { lo, hi, x, y, n };
  }, [series, dates]);
}

function path(vals: (number | null)[], x: (i: number) => number, y: (v: number) => number): string {
  let d = "", pen = false;
  vals.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`; pen = true; });
  return d;
}

function Source({ source, last, age, hi }: { source: string; last: string; age: number | null; hi: boolean }) {
  const live = source === "live";
  return (
    <span className={`pc-src ${live ? "live" : "old"}`} title={hi ? "भाव का स्रोत" : "Where these prices came from"}>
      <i /> {live ? (hi ? "Yahoo Finance से सीधे" : "Live from Yahoo Finance") : (hi ? "सहेजा हुआ डेटा" : "Saved snapshot")} · {hi ? "आख़िरी भाव" : "last close"} {fmtDate(last, hi)}
      {age != null && age > 3 ? ` (${age} ${hi ? "दिन पुराना" : "days old"})` : ""}
    </span>
  );
}

function TradingView({ symbol }: { symbol: string }) {
  const theme = useTheme((s) => s.theme);
  const hi = useLang((s) => s.lang) === "hi";
  const src = `https://s.tradingview.com/widgetembed/?symbol=${encodeURIComponent(symbol)}&interval=D&theme=${theme}&style=2&hide_side_toolbar=1&withdateranges=1&saveimage=0&locale=${hi ? "in" : "en"}&hide_top_toolbar=0`;
  return (
    <div className="pc-tv">
      <iframe title={`TradingView ${symbol}`} src={src} loading="lazy" referrerPolicy="no-referrer" />
      <p className="pc-note">{hi ? "यह ऑनलाइन चार्ट TradingView से आता है और इंटरनेट माँगता है। ख़ाली दिखे तो ऊपर का सहेजा चार्ट इस्तेमाल कीजिए।" : "This live chart comes from TradingView and needs the internet. If it stays blank, use the chart view."}</p>
    </div>
  );
}

/** One company's year of closes: area line with 50- and 200-day averages, a read-out that follows the pointer, ranges, and a switch to TradingView. */
export function PriceChart({ d }: { d: PriceData }) {
  const hi = useLang((s) => s.lang) === "hi";
  const [range, setRange] = useState("1Y");
  const [mode, setMode] = useState<"own" | "tv">("own");
  const [ma, setMa] = useState(true);
  const [hov, setHov] = useState<number | null>(null);
  const svg = useRef<SVGSVGElement>(null);

  const cut = Math.min(d.points.length, RANGES.find((r) => r[0] === range)![1]);
  const off = d.points.length - cut;
  const pts = d.points.slice(off);
  const closes = pts.map((p) => p[1]);
  const ma50 = d.ma50.slice(off), ma200 = d.ma200.slice(off);
  const sc = useScale(ma ? [closes, ma50.filter((v): v is number => v != null), ma200.filter((v): v is number => v != null)] : [closes], pts.map((p) => p[0]));
  const up = closes[closes.length - 1] >= closes[0];
  const col = up ? "var(--green)" : "var(--red)";
  const line = path(closes, sc.x, sc.y);
  const area = `${line}L${sc.x(closes.length - 1).toFixed(1)},${H - B}L${sc.x(0).toFixed(1)},${H - B}Z`;
  const ticks = nice(sc.lo, sc.hi);
  const chg = (closes[closes.length - 1] / closes[0] - 1) * 100;

  const move = (e: React.PointerEvent) => {
    const r = svg.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    setHov(Math.max(0, Math.min(closes.length - 1, Math.round(((px - L) / (W - L - R)) * (closes.length - 1)))));
  };
  const hv = hov != null ? hov : closes.length - 1;
  const cur = d.currency;
  const labelIdx = [0, Math.floor(closes.length / 3), Math.floor((2 * closes.length) / 3), closes.length - 1];

  return (
    <figure className="pc">
      <div className="pc-head">
        <div>
          <div className="pc-title">{d.name} <small>{d.ticker}</small></div>
          <div className="pc-price">{cur}{(hov != null ? closes[hv] : d.last).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
            <b className={chg >= 0 ? "up" : "dn"}>{chg >= 0 ? "▲" : "▼"} {Math.abs(chg).toFixed(1)}%</b>
            <small>{hov != null ? fmtDate(pts[hv][0], hi) : `${hi ? "पिछले" : "over"} ${range === "1Y" ? (hi ? "1 साल" : "1 year") : range}`}</small>
          </div>
        </div>
        <div className="pc-ctl">
          <div className="pc-seg" role="tablist">
            <button className={mode === "own" ? "on" : ""} onClick={() => setMode("own")}>{hi ? "चार्ट" : "Chart"}</button>
            <button className={mode === "tv" ? "on" : ""} onClick={() => setMode("tv")}>TradingView</button>
          </div>
        </div>
      </div>

      {mode === "tv" ? <TradingView symbol={d.tv} /> : (
        <>
          <div className="pc-ranges">
            {RANGES.map(([k]) => <button key={k} className={range === k ? "on" : ""} onClick={() => setRange(k)}>{k}</button>)}
            <label className="pc-ma"><input type="checkbox" checked={ma} onChange={(e) => setMa(e.target.checked)} /> {hi ? "50 और 200 दिन का औसत" : "50 & 200-day averages"}</label>
          </div>
          <svg ref={svg} viewBox={`0 0 ${W} ${H}`} className="pc-svg" role="img" aria-label={`${d.name} ${hi ? "का भाव चार्ट" : "price chart"}`}
               onPointerMove={move} onPointerLeave={() => setHov(null)}>
            <defs><linearGradient id={`pcg-${d.ticker}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={col} stopOpacity=".28" /><stop offset="1" stopColor={col} stopOpacity="0" /></linearGradient></defs>
            {ticks.map((t) => <g key={t}><line x1={L} x2={W - R} y1={sc.y(t)} y2={sc.y(t)} className="pc-grid" /><text x={W - R + 6} y={sc.y(t) + 4} className="pc-ax">{t >= 1000 ? Math.round(t).toLocaleString("en-IN") : t.toFixed(t < 100 ? 1 : 0)}</text></g>)}
            {labelIdx.map((i, k) => <text key={k} x={sc.x(i)} y={H - 6} className="pc-ax" textAnchor={k === 0 ? "start" : k === 3 ? "end" : "middle"}>{fmtDate(pts[i][0], hi)}</text>)}
            <path d={area} fill={`url(#pcg-${d.ticker})`} />
            {ma && <path d={path(ma200, sc.x, sc.y)} className="pc-ma200" />}
            {ma && <path d={path(ma50, sc.x, sc.y)} className="pc-ma50" />}
            <path d={line} className="pc-line" style={{ stroke: col }} />
            {hov != null && <g><line x1={sc.x(hv)} x2={sc.x(hv)} y1={T} y2={H - B} className="pc-cross" /><circle cx={sc.x(hv)} cy={sc.y(closes[hv])} r="4.5" style={{ fill: col }} className="pc-dot" /></g>}
          </svg>
          <div className="pc-legend">
            <span><i style={{ background: col }} />{hi ? "भाव" : "Price"}</span>
            {ma && <span><i className="m50" />{hi ? "50-दिन" : "50-day"}</span>}
            {ma && <span><i className="m200" />{hi ? "200-दिन" : "200-day"}</span>}
            <span className="pc-hl">{hi ? "साल का ऊँचा" : "Year high"} {cur}{d.high.toLocaleString("en-IN")} · {hi ? "नीचा" : "low"} {cur}{d.low.toLocaleString("en-IN")}</span>
          </div>
        </>
      )}
      <figcaption><Source source={d.source} last={d.last_date} age={d.age_days} hi={hi} /></figcaption>
    </figure>
  );
}

/** Several companies on one set of axes, each rebased to 100 on the same start date so growth can be compared like with like. */
export function CompareChart({ d }: { d: CompareData }) {
  const hi = useLang((s) => s.lang) === "hi";
  const [hov, setHov] = useState<number | null>(null);
  const [on, setOn] = useState<Record<string, boolean>>({});
  const svg = useRef<SVGSVGElement>(null);
  const shown = d.series.filter((s) => on[s.ticker] !== false);
  const n = Math.min(...d.series.map((s) => s.points.length));
  const dates = d.series[0].points.slice(-n).map((p) => p[0]);
  const vals = d.series.map((s) => s.points.slice(-n).map((p) => p[1]));
  const sc = useScale(vals.filter((_, i) => on[d.series[i].ticker] !== false), dates);
  const ticks = nice(sc.lo, sc.hi);
  const move = (e: React.PointerEvent) => {
    const r = svg.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    setHov(Math.max(0, Math.min(n - 1, Math.round(((px - L) / (W - L - R)) * (n - 1)))));
  };
  const hv = hov ?? n - 1;
  const labelIdx = [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1];
  return (
    <figure className="pc">
      <div className="pc-head">
        <div>
          <div className="pc-title">{hi ? "एक ही शुरुआत (100) से, किसकी बढ़त कितनी" : "Same start (100): how each one moved"}</div>
          <div className="pc-price"><small>{hov != null ? fmtDate(dates[hv], hi) : `${fmtDate(d.start, hi)} → ${fmtDate(d.last_date, hi)}`}</small></div>
        </div>
      </div>
      <svg ref={svg} viewBox={`0 0 ${W} ${H}`} className="pc-svg" role="img" aria-label={hi ? "तुलना चार्ट" : "Comparison chart"} onPointerMove={move} onPointerLeave={() => setHov(null)}>
        {ticks.map((t) => <g key={t}><line x1={L} x2={W - R} y1={sc.y(t)} y2={sc.y(t)} className={`pc-grid ${Math.abs(t - 100) < 1e-6 ? "base" : ""}`} /><text x={W - R + 6} y={sc.y(t) + 4} className="pc-ax">{Math.round(t)}</text></g>)}
        {labelIdx.map((i, k) => <text key={k} x={sc.x(i)} y={H - 6} className="pc-ax" textAnchor={k === 0 ? "start" : k === 3 ? "end" : "middle"}>{fmtDate(dates[i], hi)}</text>)}
        {d.series.map((s, k) => on[s.ticker] === false ? null : <path key={s.ticker} d={path(vals[k], sc.x, sc.y)} className="pc-line" style={{ stroke: LINES[k % 3] }} />)}
        {hov != null && <line x1={sc.x(hv)} x2={sc.x(hv)} y1={T} y2={H - B} className="pc-cross" />}
        {hov != null && d.series.map((s, k) => on[s.ticker] === false ? null : <circle key={s.ticker} cx={sc.x(hv)} cy={sc.y(vals[k][hv])} r="4.5" style={{ fill: LINES[k % 3] }} className="pc-dot" />)}
      </svg>
      <div className="pc-legend big">
        {d.series.map((s, k) => (
          <button key={s.ticker} className={on[s.ticker] === false ? "off" : ""} onClick={() => setOn({ ...on, [s.ticker]: on[s.ticker] === false })} aria-pressed={on[s.ticker] !== false}>
            <i style={{ background: LINES[k % 3] }} /><b>{s.name}</b> <span>{(hov != null ? vals[k][hv] : s.points[s.points.length - 1][1]).toFixed(1)}</span>
            <em className={s.change_pct >= 0 ? "up" : "dn"}>{s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(0)}%</em>
          </button>))}
      </div>
      <figcaption><Source source={d.source} last={d.last_date} age={null} hi={hi} />{shown.length < d.series.length ? "" : ""}</figcaption>
    </figure>
  );
}

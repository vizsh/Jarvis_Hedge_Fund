import { useMemo, useState } from "react";

import { useLang } from "../../lib/lang";
import { useStore } from "../../lib/store";

interface Tile { key: string; label: string; w: number; sector: string; x: number; y: number; width: number; height: number }

/** Squarified treemap: worst aspect ratio is kept as close to 1 as possible, so a 3% holding is still a visible tile. */
function squarify(items: { key: string; label: string; w: number; sector: string }[], x: number, y: number, w: number, h: number): Tile[] {
  const total = items.reduce((s, i) => s + i.w, 0) || 1;
  const out: Tile[] = [];
  let rest = [...items].sort((a, b) => b.w - a.w);
  let rx = x, ry = y, rw = w, rh = h, remaining = total;
  const worst = (row: typeof rest, side: number) => {
    const s = row.reduce((a, i) => a + i.w, 0) * (rw * rh) / remaining;
    const mx = Math.max(...row.map((i) => i.w)) * (rw * rh) / remaining, mn = Math.min(...row.map((i) => i.w)) * (rw * rh) / remaining;
    return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn));
  };
  while (rest.length) {
    const side = Math.min(rw, rh);
    let row = [rest[0]];
    let i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) { row.push(rest[i]); i++; }
    const area = (rw * rh) / remaining;
    const rowSum = row.reduce((s, r) => s + r.w, 0);
    const thick = (rowSum * area) / side;
    let off = 0;
    for (const it of row) {
      const len = (it.w * area) / thick;
      out.push(rw >= rh
        ? { ...it, x: rx, y: ry + off, width: thick, height: len }
        : { ...it, x: rx + off, y: ry, width: len, height: thick });
      off += len;
    }
    if (rw >= rh) { rx += thick; rw -= thick; } else { ry += thick; rh -= thick; }
    remaining -= rowSum;
    rest = rest.slice(row.length);
  }
  return out;
}

const HUES = [38, 214, 160, 12, 262, 96, 330, 190];

/** Where the money sits, by sector and by company. Area is share of the portfolio. A sector over the person's own cap is outlined. */
export function AllocationMap() {
  const fund = useStore((s) => s.fund);
  const hi = useLang((s) => s.lang) === "hi";
  const [hov, setHov] = useState<string | null>(null);
  const W = 760, H = 300;

  const { tiles, sectors, cap } = useMemo(() => {
    const pos = fund?.positions ?? [];
    const bySector = new Map<string, number>();
    pos.forEach((p) => bySector.set(p.sector, (bySector.get(p.sector) ?? 0) + p.weight));
    const names = [...bySector.keys()];
    const secTiles = squarify(names.map((n) => ({ key: n, label: n, w: bySector.get(n)!, sector: n })), 0, 0, W, H);
    const t: Tile[] = [];
    for (const st of secTiles) {
      const inner = pos.filter((p) => p.sector === st.key).map((p) => ({ key: p.ticker, label: p.name ?? p.ticker, w: p.weight, sector: p.sector }));
      t.push(...squarify(inner, st.x + 2, st.y + 2, Math.max(0, st.width - 4), Math.max(0, st.height - 4)));
    }
    return { tiles: t, sectors: secTiles.map((s) => ({ ...s, label: pos.find((p) => p.sector === s.key)?.sector_label ?? s.key })), cap: fund?.policy?.limits?.max_sector_pct };
  }, [fund]);

  if (!fund?.positions?.length) return null;
  const hue = (sector: string) => HUES[[...new Set(fund.positions.map((p) => p.sector))].indexOf(sector) % HUES.length];
  const cur = tiles.find((t) => t.key === hov);

  return (
    <section className="card alloc">
      <header className="alloc-head">
        <h2>{hi ? "आपका पैसा कहाँ लगा है" : "Where your money sits"}</h2>
        <p className="muted">{hi ? "हर डिब्बे का आकार पोर्टफ़ोलियो में उसका हिस्सा है। किसी पर रुकिए।" : "Each tile's size is its share of the portfolio. Hover or focus a tile."}</p>
      </header>
      <div className="alloc-stage">
        <svg viewBox={`0 0 ${W} ${H}`} className="alloc-svg" role="img" aria-label={hi ? "सेक्टर और कंपनी के हिसाब से आवंटन" : "Allocation by sector and company"}>
          {tiles.map((t) => {
            const over = cap != null && (fund.exposures[t.sector] ?? 0) > cap;
            return (
              <g key={t.key} tabIndex={0} className={`alloc-tile ${hov === t.key ? "on" : hov ? "dim" : ""}`} onPointerEnter={() => setHov(t.key)} onPointerLeave={() => setHov(null)} onFocus={() => setHov(t.key)} onBlur={() => setHov(null)}>
                <rect x={t.x} y={t.y} width={Math.max(0, t.width - 2)} height={Math.max(0, t.height - 2)} rx="5"
                      style={{ fill: `hsl(${hue(t.sector)} 38% ${hov === t.key ? 34 : 24}%)`, stroke: over ? "var(--red)" : `hsl(${hue(t.sector)} 45% 42%)` }} />
                {t.width > 70 && t.height > 34 && <text x={t.x + 9} y={t.y + 19} className="alloc-name">{(t.label.length > Math.floor(t.width / 8) ? t.label.slice(0, Math.floor(t.width / 8) - 1) + "…" : t.label)}</text>}
                {t.width > 70 && t.height > 34 && <text x={t.x + 9} y={t.y + 36} className="alloc-w">{(t.w * 100).toFixed(1)}%</text>}
              </g>);
          })}
        </svg>
        {cur && <div className="alloc-tip"><b>{cur.label}</b><span>{(cur.w * 100).toFixed(1)}% {hi ? "आपके पैसे का" : "of your money"}</span><span>{sectors.find((s) => s.key === cur.sector)?.label} · {((fund.exposures[cur.sector] ?? 0) * 100).toFixed(1)}%{cap != null ? ` / ${(cap * 100).toFixed(0)}% ${hi ? "सीमा" : "cap"}` : ""}</span></div>}
      </div>
      <ul className="alloc-legend">{sectors.map((s) => {
        const over = cap != null && (fund.exposures[s.key] ?? 0) > cap;
        return <li key={s.key} className={over ? "over" : ""}><i style={{ background: `hsl(${hue(s.key)} 55% 52%)` }} />{s.label}<b>{((fund.exposures[s.key] ?? 0) * 100).toFixed(0)}%</b>{over && <em>{hi ? "सीमा से ऊपर" : "over your cap"}</em>}</li>;
      })}</ul>
    </section>
  );
}

import { useEffect, useRef, useState } from "react";
import { createChart, type IChartApi } from "lightweight-charts";

import { Panel } from "./Panels";
import { pct, rupees } from "./Portfolio";
import { useStore } from "../lib/store";

/** Portfolio value over time, with the benchmark rebased onto the same axis.
 *
 *  Rebasing is what makes the comparison honest: two lines at different absolute
 *  scales look like a story that is not there. Both start at the same value, so the
 *  gap between them IS the relative performance.
 */
export function PortfolioChart() {
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const port = useRef<any>(null);
  const bench = useRef<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [hover, setHover] = useState<{ t: string; v?: number; b?: number } | null>(null);
  const [range, setRange] = useState<"1M" | "3M" | "6M" | "1Y">("1Y");
  const all = useRef<any[]>([]);
  const fund = useStore((s) => s.fund);
  const simClock = useStore((s) => s.simClock);

  useEffect(() => {
    if (!box.current) return;
    chart.current = createChart(box.current, {
      width: box.current.clientWidth,
      height: 230,
      layout: { background: { color: "transparent" }, textColor: "#7d7f87", fontSize: 11,
                fontFamily: "Instrument Sans, system-ui, sans-serif" },
      grid: { vertLines: { visible: false },
              horzLines: { color: "rgba(255,255,255,0.045)" } },
      rightPriceScale: { borderColor: "rgba(242, 185, 75,0.16)" },
      timeScale: { borderColor: "rgba(242, 185, 75,0.16)", fixLeftEdge: true },
      crosshair: { vertLine: { color: "rgba(242, 185, 75,0.4)", width: 1 },
                   horzLine: { color: "rgba(242, 185, 75,0.4)", width: 1 } },
      handleScroll: false, handleScale: false,
    });
    chart.current.subscribeCrosshairMove((p: any) => {
      if (!p.time || !p.seriesData) { setHover(null); return; }
      const a = p.seriesData.get(port.current), b = p.seriesData.get(bench.current);
      setHover({ t: String(p.time), v: a?.value, b: b?.value });
    });
    port.current = chart.current.addAreaSeries({
      lineColor: "#f2b94b", topColor: "rgba(242, 185, 75,0.30)",
      bottomColor: "rgba(242, 185, 75,0.0)", lineWidth: 3, priceLineVisible: false,
    });
    // Benchmark as a dashed line, deliberately quieter: it is the reference, not
    // the subject.
    bench.current = chart.current.addLineSeries({
      color: "rgba(141, 162, 255,0.85)", lineWidth: 1, lineStyle: 2,
      priceLineVisible: false, crosshairMarkerVisible: false,
    });
    const onResize = () =>
      box.current && chart.current?.applyOptions({ width: box.current.clientWidth });
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.current?.remove(); };
  }, []);

  const applyRange = () => {
    const s = all.current; if (!s.length || !chart.current) return;
    const n = { "1M": 21, "3M": 63, "6M": 126, "1Y": 250 }[range];
    const from = s[Math.max(0, s.length - n)].date, to = s[s.length - 1].date;
    chart.current.timeScale().setVisibleRange({ from, to } as any);
  };
  useEffect(applyRange, [range]);

  useEffect(() => {
    let alive = true;
    fetch("/history?days=250").then((r) => r.json()).then((d) => {
      if (!alive || !d.series?.length) return;
      port.current?.setData(d.series.map((p: any) => ({ time: p.date, value: p.value })));
      if (d.benchmark?.length) {
        bench.current?.setData(d.benchmark.map((p: any) => ({ time: p.date, value: p.value })));
      }
      all.current = d.series;
      applyRange();
      const first = d.series[0].value;
      const last = d.series[d.series.length - 1].value;
      const bFirst = d.benchmark?.[0]?.value;
      const bLast = d.benchmark?.[d.benchmark.length - 1]?.value;
      setMeta({
        change: last / first - 1,
        benchChange: bFirst && bLast ? bLast / bFirst - 1 : null,
        label: d.benchmark_label, caveat: d.caveat,
        low: Math.min(...d.series.map((p: any) => p.value)),
        high: Math.max(...d.series.map((p: any) => p.value)),
      });
    }).catch(() => {});
    return () => { alive = false; };
  }, [fund?.portfolio_id, fund?.nav, simClock]);

  return (
    <Panel title="Your money over time">
      {meta && (
        <div className="chart-head">
          <span className={meta.change >= 0 ? "up" : "down"}>
            {meta.change >= 0 ? "+" : ""}{pct(meta.change)}
          </span>
          {meta.benchChange != null && (
            <span className="tiny">
              {meta.label} {meta.benchChange >= 0 ? "+" : ""}{pct(meta.benchChange)}
              {" · "}
              <b className={meta.change - meta.benchChange >= 0 ? "up" : "down"}>
                {meta.change - meta.benchChange >= 0 ? "ahead" : "behind"} by{" "}
                {pct(Math.abs(meta.change - meta.benchChange))}
              </b>
            </span>
          )}
        </div>
      )}
      <div className="chart-readout">
        {hover && hover.v != null ? <span><b>{rupees(hover.v)}</b> · {hover.t}{hover.b != null && meta?.label ? ` · ${meta.label} ${rupees(hover.b)}` : ""}</span> : <span>Move over the chart to read any day.</span>}
        <span className="range-chips">{(["1M", "3M", "6M", "1Y"] as const).map((r) => <button key={r} className={range === r ? "on" : ""} onClick={() => setRange(r)}>{r}</button>)}</span>
      </div>
      <div className="chart-wrap" style={{ height: 230 }} ref={box} />
      {meta && (
        <div className="chart-foot">
          <span className="tiny">low {rupees(meta.low)} · high {rupees(meta.high)}</span>
          <span className="tiny legend"><i className="l-port" />you
            <i className="l-bench" />{meta.label}</span>
        </div>
      )}
      {meta?.caveat && <div className="calib-caveat">{meta.caveat}</div>}
    </Panel>
  );
}

/** Tax on a rebalance. The actionable part is rarely the total — it is "wait three
 *  weeks on this one and the rate halves". */
export function TaxPanel() {
  const [plan, setPlan] = useState<any>(null);
  const [lots, setLots] = useState<any>(null);
  const [form, setForm] = useState({ ticker: "", buy_price: "", buy_date: "" });
  const [adding, setAdding] = useState(false);
  const fund = useStore((s) => s.fund);

  const load = () => {
    fetch("/rebalance").then((r) => r.json()).then(setPlan).catch(() => {});
    fetch("/lots").then((r) => r.json()).then(setLots).catch(() => {});
  };
  useEffect(load, [fund?.portfolio_id, fund?.nav, fund?.policy?.profile]);

  const tax = plan?.tax;
  if (!tax) return null;

  const submitLot = async () => {
    if (!form.ticker || !form.buy_price || !form.buy_date) return;
    setAdding(true);
    await fetch("/lots", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: form.ticker, shares: 0,
                             buy_price: Number(form.buy_price), buy_date: form.buy_date }),
    });
    setForm({ ticker: "", buy_price: "", buy_date: "" });
    setAdding(false);
    load();
  };

  return (
    <Panel title="What the tax would cost"
           tone={tax.deferrable?.length ? "alert" : undefined}>
      {tax.total_tax > 0 ? (
        <>
          <div className="tax-total">
            <span className="tt-value">{rupees(tax.total_tax)}</span>
            <span className="tiny">estimated capital gains tax on this rebalance</span>
          </div>
          <div className="kv"><span className="k">Short term (20%)</span>
            <span className="v">{rupees(tax.short_term_tax)}</span></div>
          <div className="kv"><span className="k">Long term (12.5%)</span>
            <span className="v">{rupees(tax.long_term_tax)}</span></div>
          {tax.exemption_used > 0 && (
            <div className="kv"><span className="k">Exemption used</span>
              <span className="v up">{rupees(tax.exemption_used)} of{" "}
                {rupees(tax.exemption_limit)}</span></div>
          )}
          {tax.sector_points_gained > 0 && (
            <div className="kv"><span className="k">Cost per point of risk removed</span>
              <span className="v">{rupees(tax.tax_per_point ?? 0)}</span></div>
          )}
        </>
      ) : (
        <div className="empty">
          {tax.unknown_basis
            ? "No tax estimate yet — I do not know what you paid."
            : "No taxable gain on these sells."}
        </div>
      )}

      {!!tax.deferrable?.length && (
        <div className="defer">
          <div className="code">Wait, and pay less</div>
          {tax.deferrable.slice(0, 3).map((d: any) => (
            <div className="defer-row" key={d.ticker}>
              <b>{d.name}</b> — hold {d.days_to_wait} more days and the rate halves,
              saving about <b>{rupees(d.saving)}</b>.
            </div>
          ))}
        </div>
      )}

      {!!tax.unknown_basis && (
        <div className="tiny" style={{ marginTop: 8 }}>
          {tax.unknown_basis} holding(s) have no purchase price, so their tax is unknown.
          I will not guess at it.
        </div>
      )}

      {!!lots?.missing?.length && (
        <div className="lot-form">
          <select className="field" value={form.ticker}
                  onChange={(e) => setForm({ ...form, ticker: e.target.value })}>
            <option value="">Add what you paid…</option>
            {lots.missing.map((m: any) => (
              <option key={m.ticker} value={m.ticker}>{m.name}</option>
            ))}
          </select>
          <input className="field" type="number" placeholder="price"
                 value={form.buy_price}
                 onChange={(e) => setForm({ ...form, buy_price: e.target.value })} />
          <input className="field" type="date" value={form.buy_date}
                 onChange={(e) => setForm({ ...form, buy_date: e.target.value })} />
          <button className="btn go" disabled={adding} onClick={submitLot}>Save</button>
        </div>
      )}

      <div className="calib-caveat">{tax.caveat}</div>
    </Panel>
  );
}

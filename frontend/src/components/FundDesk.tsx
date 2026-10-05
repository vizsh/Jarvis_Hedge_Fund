import { useEffect, useState } from "react";

import { Panel } from "./Panels";
import { pct, rupees } from "./Portfolio";
import { useStore } from "../lib/store";

/** The rebalancer: the portfolio manager's construction job, shown as a plan you can
 *  read before you book it. Before/after is the whole point — a list of trades without
 *  the effect they have is just a list of trades. */
export function RebalancePanel() {
  const [plan, setPlan] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState<any>(null);
  const fund = useStore((s) => s.fund);

  const load = () => {
    setApplied(null);
    fetch("/rebalance").then((r) => r.json()).then(setPlan).catch(() => {});
  };
  useEffect(load, [fund?.nav, fund?.portfolio_id, fund?.policy?.profile]);

  if (!plan) return null;
  if (!plan.trade_count) {
    return (
      <Panel title="Rebalance" tone="ok">
        <div className="empty">{plan.notes?.[0] ?? "Nothing to do."}</div>
      </Panel>
    );
  }

  const apply = async () => {
    setBusy(true);
    const res = await fetch("/rebalance/apply", { method: "POST" });
    setApplied(await res.json());
    setBusy(false);
  };

  const delta = (key: string, invert = false) => {
    const a = plan.before[key], b = plan.after[key];
    if (a == null || b == null) return null;
    const better = invert ? b < a : b > a;
    return <span className={better ? "up" : b === a ? "" : "down"}>
      {(b > a ? "↑" : b < a ? "↓" : "→")}
    </span>;
  };

  return (
    <Panel title="Rebalance plan" tone={plan.compliant_after ? "ok" : "alert"}>
      <div className="plan-head">
        <span>{plan.trade_count} trades</span>
        <span>{rupees(plan.turnover)} turnover</span>
        <span className="tiny">cost {rupees(plan.cost)}</span>
      </div>

      <div className="ba-grid">
        <div className="ba-col">
          <div className="ba-label">now</div>
          <div className="ba-row"><span>top sector</span><b>{pct(plan.before.top_sector)}</b></div>
          <div className="ba-row"><span>top stock</span><b>{pct(plan.before.top_position)}</b></div>
          <div className="ba-row"><span>behaves like</span><b>{plan.before.effective_holdings}</b></div>
          <div className="ba-row"><span>cash</span><b>{pct(plan.before.cash_pct)}</b></div>
        </div>
        <div className="ba-arrows">
          <div>{delta("top_sector", true)}</div>
          <div>{delta("top_position", true)}</div>
          <div>{delta("effective_holdings")}</div>
          <div>{delta("cash_pct")}</div>
        </div>
        <div className="ba-col after">
          <div className="ba-label">after</div>
          <div className="ba-row"><span>top sector</span><b>{pct(plan.after.top_sector)}</b></div>
          <div className="ba-row"><span>top stock</span><b>{pct(plan.after.top_position)}</b></div>
          <div className="ba-row"><span>behaves like</span><b>{plan.after.effective_holdings}</b></div>
          <div className="ba-row"><span>cash</span><b>{pct(plan.after.cash_pct)}</b></div>
        </div>
      </div>

      <div className="trades">
        {plan.trades.map((t: any, i: number) => (
          <div className={`trade ${t.side.toLowerCase()}`} key={i}>
            <span className="t-side">{t.side}</span>
            <span className="t-qty">{t.shares}</span>
            <span className="t-name">{t.name}</span>
            <span className="t-val">{rupees(t.value)}</span>
            <div className="t-why">{t.reason}</div>
          </div>
        ))}
      </div>

      {plan.notes?.map((n: string, i: number) => (
        <div className="tiny" key={i} style={{ marginTop: 6 }}>{n}</div>
      ))}

      {applied ? (
        <div className="remedy" style={{ marginTop: 9 }}>
          <div className="code">Booked to the paper ledger</div>
          {applied.booked?.length} trades booked
          {applied.refused?.length ? `, ${applied.refused.length} refused by the firewall` : ""}.
          New value {rupees(applied.nav_after ?? 0)}.
        </div>
      ) : (
        <button className="btn go" style={{ marginTop: 9, width: "100%" }}
                disabled={busy} onClick={apply}>
          {busy ? "Booking…" : "Book this plan (paper)"}
        </button>
      )}
    </Panel>
  );
}

/** Correlation. "You own eight stocks" is a count; "four move together at 0.9" is a
 *  fact that changes what you do next. */
export function CorrelationPanel() {
  const [data, setData] = useState<any>(null);
  const fund = useStore((s) => s.fund);

  useEffect(() => {
    fetch("/correlation").then((r) => r.json()).then(setData).catch(() => {});
  }, [fund?.portfolio_id, fund?.nav]);

  if (!data?.pairs?.length) return null;
  const tickers = Object.keys(data.names ?? {});

  const cell = (a: string, b: string) => {
    if (a === b) return { bg: "rgb(var(--wash) / 0.10)", v: 1 };
    const r = data.matrix?.[a]?.[b];
    if (r == null) return { bg: "transparent", v: null };
    // Red for "these are the same bet", blue for genuinely independent.
    const t = Math.max(0, Math.min(1, (r + 0.2) / 1.2));
    return { bg: `rgba(${Math.round(60 + 195 * t)}, ${Math.round(190 - 130 * t)}, ${Math.round(230 - 140 * t)}, ${0.18 + 0.6 * t})`, v: r };
  };

  return (
    <Panel title="What moves together" tone={data.avg_correlation > 0.55 ? "alert" : undefined}>
      <div className="kv">
        <span className="k">Average correlation</span>
        <span className="v" style={{ color: data.avg_correlation > 0.55 ? "var(--red)" : "var(--green)" }}>
          {data.avg_correlation ?? "—"}
        </span>
      </div>
      <div className="tiny" style={{ marginBottom: 8 }}>
        1.0 means two holdings move as one. Lower is more genuinely spread out.
      </div>

      {tickers.length <= 14 && (
        <div className="heat" style={{ gridTemplateColumns: `repeat(${tickers.length}, 1fr)` }}>
          {tickers.map((a) => tickers.map((b) => {
            const c = cell(a, b);
            return <div key={`${a}-${b}`} className="heat-cell" style={{ background: c.bg }}
                        title={`${data.names[a]} / ${data.names[b]}: ${c.v ?? "n/a"}`} />;
          }))}
        </div>
      )}

      {data.pairs.slice(0, 4).map((p: any, i: number) => (
        <div className="pair" key={i}>
          <div className="pair-names">{p.a_name} <span className="amp">&amp;</span> {p.b_name}</div>
          <div className="pair-meta">
            <span className="pair-r" style={{ color: p.correlation > 0.85 ? "var(--red)" : "var(--amber)" }}>
              {p.correlation}
            </span>
            <span className="tiny">{pct(p.combined_weight)} of your money</span>
            {p.same_sector && <span className="tiny">same industry</span>}
          </div>
        </div>
      ))}
    </Panel>
  );
}

/** Screener — the analyst's desk, in arithmetic. */
export function ScreenerPanel() {
  const [kind, setKind] = useState("diversifiers");
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const fund = useStore((s) => s.fund);

  const run = (k: string) => {
    setKind(k); setBusy(true);
    fetch(`/screen/${k}`).then((r) => r.json()).then(setData)
      .finally(() => setBusy(false));
  };
  useEffect(() => run(kind), [fund?.portfolio_id]);

  const screens = data?.screens ?? {};
  return (
    <Panel title="Find something new">
      <div className="ask-chips">
        {Object.entries(screens).map(([k, label]) => (
          <div key={k} className={`ask-chip ${kind === k ? "on" : ""}`}
               title={label as string} onClick={() => run(k)}>
            {k.replace("_", " ")}
          </div>
        ))}
      </div>
      {data?.label && <div className="tiny" style={{ margin: "8px 0" }}>{data.label}</div>}
      {busy && <div className="empty">Ranking the universe…</div>}
      {(data?.results ?? []).slice(0, 6).map((r: any) => (
        <div className="screen-row" key={r.ticker}>
          <span className="s-name">{r.name}</span>
          <span className="tiny">{r.sector_label}</span>
          <span className="num">
            {r.avg_correlation_to_book != null ? `r ${r.avg_correlation_to_book}`
              : r.ret_3m != null ? `${(r.ret_3m * 100).toFixed(0)}%`
              : r.rsi != null ? `RSI ${r.rsi}` : ""}
          </span>
        </div>
      ))}
    </Panel>
  );
}

/** Attribution — where the money came from. */
export function AttributionPanel() {
  const [data, setData] = useState<any>(null);
  const [window_, setWindow] = useState("3m");
  const fund = useStore((s) => s.fund);

  useEffect(() => {
    fetch(`/attribution?window=${window_}`).then((r) => r.json()).then(setData).catch(() => {});
  }, [window_, fund?.portfolio_id, fund?.nav]);

  if (!data?.contributions?.length) return null;
  const best = data.contributions.slice(0, 3);
  const worst = data.contributions.slice(-3).reverse();
  const max = Math.max(...data.by_sector.map((s: any) => Math.abs(s.contribution)), 0.001);

  return (
    <Panel title="Where it came from">
      <div className="seg" style={{ marginBottom: 9 }}>
        {["1m", "3m", "6m", "1y"].map((w) => (
          <div key={w} className={`seg-item ${window_ === w ? "on" : ""}`}
               onClick={() => setWindow(w)}>{w}</div>
        ))}
      </div>

      <div className="attr-head">
        <span className={data.portfolio_return >= 0 ? "up" : "down"}>
          {(data.portfolio_return * 100).toFixed(1)}%
        </span>
        {data.benchmark_return != null && (
          <span className="tiny">
            {data.benchmark_label} {(data.benchmark_return * 100).toFixed(1)}% ·{" "}
            <b className={data.excess >= 0 ? "up" : "down"}>
              {data.excess >= 0 ? "+" : ""}{(data.excess * 100).toFixed(1)} vs market
            </b>
          </span>
        )}
      </div>

      {data.by_sector.slice(0, 6).map((s: any) => (
        <div className="attr-row" key={s.sector}>
          <span className="a-name">{s.sector_label}</span>
          <span className="a-bar">
            <span className={s.contribution >= 0 ? "pos" : "neg"}
                  style={{ width: `${(Math.abs(s.contribution) / max) * 100}%` }} />
          </span>
          <span className="num">{(s.contribution * 100).toFixed(2)}%</span>
        </div>
      ))}

      <div className="kv" style={{ marginTop: 8 }}>
        <span className="k">Helped most</span>
        <span className="v up">{best.map((c: any) => c.name).join(", ")}</span>
      </div>
      <div className="kv">
        <span className="k">Hurt most</span>
        <span className="v down">{worst.map((c: any) => c.name).join(", ")}</span>
      </div>
      <div className="calib-caveat">{data.caveat}</div>
    </Panel>
  );
}

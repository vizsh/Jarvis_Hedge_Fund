import { useEffect, useRef, useState } from "react";
import { createChart, type IChartApi } from "lightweight-charts";

import { useStore } from "../lib/store";
import { loadPrices } from "../lib/socket";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const money = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 0 });

export function Panel({ title, children, tone, className = "" }: {
  title: string; children: React.ReactNode; tone?: "alert" | "ok"; className?: string;
}) {
  return (
    <div className={`panel ${tone ?? ""} ${className}`}>
      <div className="panel-title">{title}</div>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ boot */
export function BootSequence() {
  const boot = useStore((s) => s.boot);
  const sources = useStore((s) => s.sources);
  if (!boot.length) return null;
  return (
    <div className="boot">
      {boot.map((l, i) => (
        <div key={i} className={`boot-line ${l.level}`} style={{ animationDelay: `${i * 0.05}s` }}>
          {l.line}
        </div>
      ))}
      {sources.map((s, i) => (
        <div key={s.source} className="boot-line ok" style={{ animationDelay: `${(boot.length + i) * 0.05}s` }}>
          {`  ${s.source.padEnd(24, ".")} ${s.rows.toLocaleString()} rows`}
        </div>
      ))}
      <div className="boot-line" style={{ animationDelay: "0.9s" }}>
        <span className="boot-cursor" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ desks */
export function DeskPanel() {
  const desks = useStore((s) => s.desks);
  const names = ["Fundamental", "Quant", "Narrative", "Red Team"];
  return (
    <Panel title="Analyst Desks">
      {names.map((n) => {
        const d = desks[n];
        return (
          <div className="desk" key={n}>
            <div className={`led ${d?.state ?? "idle"}`} />
            <div className="name">{n}</div>
            <div className="ms">{d?.note ?? "—"}</div>
          </div>
        );
      })}
    </Panel>
  );
}

/* ------------------------------------------------------------------ claims */
export function ClaimsPanel() {
  const claims = useStore((s) => s.claims);
  const rejected = useStore((s) => s.rejected);
  const evidence = useStore((s) => s.evidence);
  const select = useStore((s) => s.select);

  return (
    <Panel title="Claims &amp; Citations" className="scroll" >
      {!claims.length && !rejected.length && (
        <div className="empty">No investigation yet. Ask JARVIS to analyse a ticker.</div>
      )}
      {claims.map((c, i) => (
        <div className={`claim ${c.stance}`} key={i}>
          <div className="meta">
            <span>{c.desk}</span>
            <span>{c.stance}</span>
            <span>w {c.weight.toFixed(2)}</span>
          </div>
          <div>{c.claim}</div>
          <div className="meta" style={{ marginTop: 5 }}>
            {c.source_ids.map((id) => (
              <span
                className="cites"
                key={id}
                onClick={() => {
                  const item = evidence[id];
                  if (item) {
                    select({ id, label: item.text, kind: "fact",
                             detail: `${item.source_name} · ${item.published_at.slice(0, 10)}`,
                             uri: item.source_uri });
                  }
                }}
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      ))}
      {rejected.map((r, i) => (
        <div className="claim dropped" key={`r${i}`}>
          <div className="meta">
            <span>{r.desk}</span>
            <span>dropped · {r.reason.replace("_", " ")}</span>
          </div>
          <div>{r.claim}</div>
        </div>
      ))}
    </Panel>
  );
}

/* ------------------------------------------------------------------ verdict */
export function ConvictionPanel() {
  const c = useStore((s) => s.conviction);
  if (!c) return null;
  const bar = (label: string, value: number, cls = "") => (
    <div className="meter">
      <div className="row"><span>{label}</span><b>{value.toFixed(2)}</b></div>
      <div className="track"><div className={`fill ${cls}`} style={{ width: `${Math.abs(value) * 100}%` }} /></div>
    </div>
  );
  return (
    <Panel title="Committee Verdict" tone={c.groupthink ? "alert" : undefined}>
      {bar("Conviction", c.score, c.score > 0.5 ? "good" : "")}
      {bar("Agreement", c.agreement, c.groupthink ? "warn" : "")}
      {bar("Evidence quality", c.evidence_quality)}
      <div className="meter">
        <div className="row">
          <span>Net stance</span>
          <b style={{ color: c.net_stance > 0 ? "var(--green)" : "var(--red)" }}>
            {c.net_stance > 0 ? "+" : ""}{c.net_stance.toFixed(2)}
          </b>
        </div>
        <div className="track">
          <div className={`fill ${c.net_stance > 0 ? "good" : "bad"}`}
               style={{ width: `${Math.abs(c.net_stance) * 100}%` }} />
        </div>
      </div>
      <div className="kv"><span className="k">accepted / dropped</span>
        <span className="v">{c.claims_accepted} / {c.claims_rejected}</span></div>
      {c.groupthink && (
        <div className="groupthink">
          <b>Analyst unanimity — low information</b>
          {c.dissent
            ? "The three analyst desks agreed. Correlated agents drawing on the same model and the same evidence agree more than independent analysts would, so conviction is discounted even though a counter-case exists."
            : "The three analyst desks agreed and the red team found no counter-case. Conviction has been discounted rather than confirmed."}
        </div>
      )}
      {c.dissent && (
        <div className="groupthink dissent">
          <b>Red team — forced counter-case</b>
          {c.dissent}
          <div className="tiny" style={{ marginTop: 5 }}>
            Runs second, on the analysts' actual output, and must argue the opposite side.
          </div>
        </div>
      )}
      {!!c.conceded && (
        <div className="groupthink" style={{ marginTop: 8 }}>
          <b>Red team conceded {c.conceded}</b>
          It tried to side with the consensus it was told to oppose — the honest signal
          that it could not build a counter-case from this evidence.
        </div>
      )}
    </Panel>
  );
}

/* ------------------------------------------------------------------ risk */
export function RiskPanel() {
  const d = useStore((s) => s.decision);
  const p = useStore((s) => s.proposal);
  if (!d) return null;
  const cf = d.counterfactual;
  return (
    <Panel title="Risk Firewall" tone={d.approved ? "ok" : "alert"}>
      <div className={`verdict ${d.approved ? "approved" : "rejected"}`}>
        {d.approved ? "APPROVED" : "REJECTED"}
      </div>
      {p && (
        <div className="kv">
          <span className="k">{p.side} {p.shares} {p.ticker}</span>
          <span className="v">@ {p.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
        </div>
      )}
      <div className="kv"><span className="k">policy</span><span className="v">{d.policy_version}</span></div>

      {d.violations.map((v) => (
        <div className="violation" key={v.code}>
          <div className="code">{v.code}</div>
          <div className="msg">{v.message}</div>
          <div className="meter" style={{ marginBottom: 0 }}>
            <div className="row">
              <span>measured</span><b>{pct(v.measured)} vs {pct(v.limit)} cap</b>
            </div>
            <div className="track">
              <div className="fill bad" style={{ width: `${Math.min(100, (v.measured / v.limit) * 100)}%` }} />
            </div>
          </div>
        </div>
      ))}

      {d.remedy && d.remedy.max_shares > 0 && (
        <div className="remedy">
          <div className="code">Remedy · {d.remedy.binding_constraint}</div>
          {d.remedy.explanation}
        </div>
      )}

      {cf && (
        <div className="remedy" style={{ marginTop: 8, borderColor: "var(--violet)" }}>
          <div className="code" style={{ color: "var(--violet)" }}>Policy simulator</div>
          {Object.entries(cf.overrides).map(([k, v]) => (
            <div key={k}>{k.replace(/_/g, " ")} → {pct(v)}</div>
          ))}
          <div style={{ marginTop: 6 }}>
            under <b>{cf.from}</b>: {cf.was_approved ? "approved" : "rejected"} →
            under <b>{cf.to}</b>: {cf.now_approved ? "approved" : "rejected"}
          </div>
        </div>
      )}
    </Panel>
  );
}

/* ------------------------------------------------------------------ fund */
export function FundPanel() {
  const fund = useStore((s) => s.fund);
  if (!fund) return <Panel title="Fund"><div className="empty">Connecting…</div></Panel>;
  const cap = fund.policy.limits.max_sector_pct ?? 0.3;
  return (
    <Panel title="Fund State">
      <div className="kv"><span className="k">NAV</span><span className="v">{money(fund.nav)}</span></div>
      <div className="kv"><span className="k">Cash</span><span className="v">{pct(fund.cash_pct)}</span></div>
      <div style={{ marginTop: 9 }} className="tiny">Sector exposure vs {pct(cap)} cap</div>
      {Object.entries(fund.exposures).sort((a, b) => b[1] - a[1]).map(([sector, w]) => (
        <div className="expo" key={sector}>
          <div className="track">
            <div className={`fill ${w > cap ? "over" : ""}`} style={{ width: `${Math.min(100, (w / 0.45) * 100)}%` }} />
            <div className="cap" style={{ left: `${(cap / 0.45) * 100}%` }} />
            <div className="lbl"><span>{sector}</span><span className="num">{pct(w)}</span></div>
          </div>
        </div>
      ))}
    </Panel>
  );
}

export function PositionsPanel() {
  const fund = useStore((s) => s.fund);
  if (!fund?.positions?.length) return null;
  const cap = fund.policy.limits.max_position_pct ?? 0.05;
  return (
    <Panel title="Positions" className="scroll">
      {fund.positions.sort((a, b) => b.weight - a.weight).map((p) => (
        <div className="kv" key={p.ticker}>
          <span className="k">{p.ticker.replace(".NS", "")}</span>
          <span className="v" style={{ color: p.weight > cap ? "var(--red)" : undefined }}>
            {p.shares} · {pct(p.weight)}
          </span>
        </div>
      ))}
    </Panel>
  );
}

/* ------------------------------------------------------------------ chart */
export function PriceChart() {
  const ticker = useStore((s) => s.ticker);
  const simClock = useStore((s) => s.simClock);
  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<any>(null);

  useEffect(() => {
    if (!box.current) return;
    chart.current = createChart(box.current, {
      width: box.current.clientWidth,
      height: 150,
      layout: { background: { color: "transparent" }, textColor: "#6c8296", fontSize: 9,
                fontFamily: "JetBrains Mono, monospace" },
      grid: { vertLines: { color: "rgba(120,160,190,0.06)" },
              horzLines: { color: "rgba(120,160,190,0.06)" } },
      rightPriceScale: { borderColor: "rgba(37,217,255,0.16)" },
      timeScale: { borderColor: "rgba(37,217,255,0.16)", fixLeftEdge: true },
      crosshair: { vertLine: { color: "rgba(37,217,255,0.4)", width: 1 },
                   horzLine: { color: "rgba(37,217,255,0.4)", width: 1 } },
      handleScroll: false, handleScale: false,
    });
    series.current = chart.current.addAreaSeries({
      lineColor: "#25d9ff", topColor: "rgba(37,217,255,0.28)",
      bottomColor: "rgba(37,217,255,0.01)", lineWidth: 2,
    });
    const onResize = () => box.current && chart.current?.applyOptions({ width: box.current.clientWidth });
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.current?.remove(); };
  }, []);

  useEffect(() => {
    // Reloads on every clock change: the series is point-in-time filtered server-side,
    // so rewinding visibly truncates the line rather than just moving a marker.
    let alive = true;
    loadPrices(ticker).then((bars) => {
      if (alive && series.current && bars.length) {
        series.current.setData(bars);
        chart.current?.timeScale().fitContent();
      }
    });
    return () => { alive = false; };
  }, [ticker, simClock]);

  return (
    <Panel title={`${ticker.replace(".NS", "")} · point-in-time`}>
      <div className="chart-wrap" ref={box} />
    </Panel>
  );
}

/* ------------------------------------------------------------------ log */
export function LogPanel() {
  const log = useStore((s) => s.log);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { if (box.current) box.current.scrollTop = box.current.scrollHeight; }, [log]);
  return (
    <Panel title="Execution Log" className="scroll">
      <div ref={box} style={{ maxHeight: "100%" }}>
        {log.slice(-60).map((l, i) => (
          <div className={`logline ${l.level ?? ""}`} key={`${l.seq}-${i}`}>
            <span className="k">{l.kind}</span>
            <span className="t">{l.text}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function SourcesPanel() {
  const sources = useStore((s) => s.sources);
  const fund = useStore((s) => s.fund);
  if (!sources.length) return null;
  return (
    <Panel title="Data Sources">
      {sources.map((s) => (
        <div className="source-row" key={s.source}>
          <div className={`dot ${s.online ? "live" : "dead"}`} />
          <div className="nm">{s.source}</div>
          <div className="rc">{s.rows.toLocaleString()}</div>
        </div>
      ))}
      {fund && (
        <div className="kv" style={{ marginTop: 7, borderTop: "1px solid var(--rule-soft)", paddingTop: 6 }}>
          <span className="k">visible at clock</span>
          <span className="v">{(fund.visible.prices + fund.visible.signals).toLocaleString()}</span>
        </div>
      )}
    </Panel>
  );
}

/* ------------------------------------------------------------------ execution */
export function ExecutionPanel() {
  const x = useStore((s) => s.execution);
  if (!x) return null;
  return (
    <Panel title="Paper Ledger" tone="ok">
      <div className="paper-stamp">PAPER ONLY</div>
      <div className="verdict approved" style={{ fontSize: 17 }}>FILLED</div>
      <div className="kv"><span className="k">{x.side} {x.shares} {x.ticker}</span>
        <span className="v">@ {x.price.toFixed(2)}</span></div>
      <div className="kv"><span className="k">NAV after</span><span className="v">{money(x.nav_after)}</span></div>
      <div className="tiny" style={{ marginTop: 7 }}>No broker was contacted.</div>
    </Panel>
  );
}

/* ------------------------------------------------------------------ inspector */
export function Inspector() {
  const node = useStore((s) => s.selected);
  const select = useStore((s) => s.select);
  if (!node) return null;
  return (
    <div className="inspector">
      <Panel title="Evidence · provenance">
        <div className="src">{node.id} · {node.detail}</div>
        <div className="txt">{node.label}</div>
        {node.uri && <a href={node.uri} target="_blank" rel="noreferrer">{node.uri.slice(0, 80)}</a>}
        <div style={{ marginTop: 8 }}>
          <button className="btn" onClick={() => select(null)}>Close</button>
        </div>
      </Panel>
    </div>
  );
}

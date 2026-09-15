import { useEffect, useState } from "react";

import { useGuide } from "../lib/guide";
import { pct, rupees } from "./Portfolio";

/** One page: printable, shareable, dateable.
 *
 *  Everything else here lives on a screen that is always moving, which is right for
 *  working and wrong for the two moments that actually matter — showing someone else
 *  what you own, and looking back in six months at what you were told. This renders
 *  the same on paper as on glass, and carries its own provenance so it is a record
 *  rather than an opinion. */
export function ReportView() {
  const open = useGuide((s) => s.report);
  const close = () => useGuide.getState().setReport(false);
  const [d, setD] = useState<any>(null);

  useEffect(() => {
    if (!open) { setD(null); return; }
    fetch("/report").then((r) => r.json()).then(setD).catch(() => setD(null));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  return (
    <div className="rep-wrap" onClick={close}>
      <div className="rep" onClick={(e) => e.stopPropagation()}>
        {!d && <div className="dd-load">building…</div>}
        {d?.empty && <div className="dd-load">Nothing to report — no holdings yet.</div>}

        {d && !d.empty && (
          <>
            <div className="rep-bar no-print">
              <button className="btn go sm" onClick={() => window.print()}>Print</button>
              <button className="btn sm ghost" onClick={close}>Close</button>
            </div>

            <header className="rep-head">
              <div>
                <h1>{d.title}</h1>
                <div className="rep-meta">
                  Prices as of {d.as_of} · generated {d.generated_at}
                </div>
              </div>
              <div className="rep-grade">
                <span className={`grade g${d.headline.grade}`}>{d.headline.grade}</span>
                <span className="rep-score">{d.headline.score}<i>/100</i></span>
              </div>
            </header>

            <p className="rep-verdict">{d.headline.verdict}</p>

            <section className="rep-stats">
              <Stat label="Total value" value={d.headline.nav_display} />
              <Stat label="Holdings" value={`${d.headline.holdings} in ${d.headline.sectors} industries`} />
              <Stat label="Behaves like" value={`${d.headline.effective_holdings} positions`} />
              <Stat label="Cash" value={pct(d.headline.cash_pct)} />
              {d.headline.beta != null && <Stat label="Market sensitivity" value={`${d.headline.beta}x`} />}
              {d.headline.max_drawdown != null &&
                <Stat label="Worst fall so far" value={pct(Math.abs(d.headline.max_drawdown))} />}
            </section>

            <section className="rep-sec">
              <h2>Measured against</h2>
              <p className="rep-body">{d.policy.name} — {d.policy.describes}</p>
            </section>

            {!!d.findings?.length && (
              <section className="rep-sec">
                <h2>What stands out</h2>
                {d.findings.map((f: any, i: number) => (
                  <div className={`rep-find ${f.severity}`} key={i}>
                    <b>{f.headline}.</b> {f.detail}
                  </div>
                ))}
              </section>
            )}

            {!!d.actions?.length && (
              <section className="rep-sec">
                <h2>What to do about it</h2>
                <ol className="rep-actions">
                  {d.actions.map((a: any) => (
                    <li key={a.id}>
                      <b>{a.title}.</b> {a.detail}
                      <div className="rep-why">{a.why}</div>
                    </li>
                  ))}
                </ol>
              </section>
            )}

            <section className="rep-sec">
              <h2>What you own</h2>
              <table className="rep-table">
                <thead>
                  <tr><th>Holding</th><th>Industry</th><th className="r">Shares</th>
                      <th className="r">Value</th><th className="r">Weight</th></tr>
                </thead>
                <tbody>
                  {d.positions.map((p: any) => (
                    <tr key={p.ticker}>
                      <td>{p.name}</td><td>{p.sector}</td>
                      <td className="r">{p.shares}</td>
                      <td className="r">{rupees(p.value)}</td>
                      <td className="r">{pct(p.weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {!!d.stress?.scenarios?.length && (
              <section className="rep-sec">
                <h2>What it has survived</h2>
                <table className="rep-table">
                  <thead><tr><th>Scenario</th><th>Type</th><th className="r">Effect</th>
                             <th className="r">Change</th></tr></thead>
                  <tbody>
                    {d.stress.scenarios.map((s: any, i: number) => (
                      <tr key={i}>
                        <td>{s.label}</td>
                        <td className="tiny">{s.kind === "historical" ? "really happened" : "what-if"}</td>
                        <td className="r" style={{ color: s.portfolio_return < 0 ? "#b00020" : "#0a7d35" }}>
                          {pct(s.portfolio_return)}
                        </td>
                        <td className="r">{rupees(s.value_change)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            {!!d.plan?.trade_count && (
              <section className="rep-sec">
                <h2>The plan on file</h2>
                <p className="rep-body">
                  {d.plan.trade_count} trades, {rupees(d.plan.turnover)} of turnover,
                  {" "}{rupees(d.plan.cost)} in costs.
                  {d.plan.compliant_after
                    ? " This brings every limit back inside range."
                    : " This improves matters but does not clear every limit."}
                  {d.plan.tax?.total_tax > 0 && ` Estimated tax: ${rupees(d.plan.tax.total_tax)}.`}
                </p>
              </section>
            )}

            {d.attribution?.summary && (
              <section className="rep-sec">
                <h2>Where returns came from</h2>
                <p className="rep-body">{d.attribution.summary}</p>
              </section>
            )}

            <footer className="rep-foot">
              <div><b>How this was produced.</b> {d.provenance.rule}</div>
              <div className="rep-caveat">{d.provenance.caveat}</div>
              <div className="tiny">
                Simulation clock {String(d.provenance.clock).slice(0, 10)} ·
                benchmark {d.provenance.benchmark} ·
                {d.provenance.visible?.prices?.toLocaleString()} prices and
                {" "}{d.provenance.visible?.signals?.toLocaleString()} signals visible at
                this clock.
              </div>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rep-stat">
      <div className="rep-stat-label">{label}</div>
      <div className="rep-stat-value">{value}</div>
    </div>
  );
}

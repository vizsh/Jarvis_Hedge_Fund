import { useEffect, useState } from "react";

import { useGuide } from "../lib/guide";
import { pct, rupees } from "./Portfolio";

/** Make any number on screen a door into what it is made of.
 *
 *  The glass-box claim was previously spent on a separate "Machinery" mode that a
 *  normal user never opens — which is the wrong place for it. Transparency is only
 *  worth anything at the moment somebody doubts a specific figure, and the way to
 *  serve that moment is to let them click the figure itself. */
export function Num({ metric, value, k, className = "" }: {
  metric: string; value: React.ReactNode; k?: string; className?: string;
}) {
  const openDrill = useGuide((s) => s.openDrill);
  return (
    <span className={`num-drill ${className}`} title="Where does this number come from?"
          onClick={(e) => { e.stopPropagation(); openDrill(metric, k); }}>
      {value}
    </span>
  );
}

export function DrillDown() {
  const drill = useGuide((s) => s.drill);
  const close = useGuide((s) => s.closeDrill);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!drill) { setData(null); return; }
    const url = `/drilldown/${drill.metric}` + (drill.key ? `?key=${drill.key}` : "");
    fetch(url).then((r) => r.json()).then(setData).catch(() => setData(null));
  }, [drill?.metric, drill?.key]);

  useEffect(() => {
    if (!drill) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drill, close]);

  if (!drill) return null;

  return (
    <div className="dd-wrap" onClick={close}>
      <div className="dd" onClick={(e) => e.stopPropagation()}>
        {!data && <div className="dd-load">opening…</div>}
        {data?.error && <div className="dd-load">{data.error}</div>}

        {data && !data.error && (
          <>
            <div className="dd-top">
              <div>
                <div className="dd-title">{data.title}</div>
                <div className="dd-value">
                  {data.display}
                  {data.limit_display && (
                    <span className={`dd-limit ${data.over_by > 0 ? "over" : ""}`}>
                      limit {data.limit_display}
                      {data.over_by > 0 && ` · over by ${pct(data.over_by)}`}
                    </span>
                  )}
                </div>
              </div>
              <button className="flow-x" onClick={close}>✕</button>
            </div>

            {!!data.components?.length && (
              <div className="dd-section">
                <div className="dd-label">What it is made of</div>
                {data.components.map((c: any, i: number) => (
                  <div className="dd-comp" key={i}>
                    <div className="dd-comp-main">
                      <span className="dd-comp-label">{c.label}</span>
                      <span className="dd-comp-value">
                        {typeof c.value === "number" && Math.abs(c.value) > 999
                          ? rupees(c.value)
                          : typeof c.value === "number" && Math.abs(c.value) <= 1 && c.value !== 0
                            ? pct(c.value)
                            : c.value}
                      </span>
                    </div>
                    {c.sub && <div className="dd-comp-sub">{c.sub}</div>}
                  </div>
                ))}
              </div>
            )}

            <div className="dd-section">
              <div className="dd-label">How it was worked out</div>
              <div className="dd-formula">{data.formula}</div>
            </div>

            <div className="dd-section">
              <div className="dd-label">Why it matters</div>
              <div className="dd-why">{data.why}</div>
            </div>

            {data.provenance && (
              <div className="dd-prov">
                <div className="dd-label">
                  Where it came from
                  <span className={`dd-tier t-${data.provenance.tier}`}>
                    {data.provenance.tier}
                  </span>
                </div>
                <div className="dd-prov-rule">{data.provenance.rule}</div>
                {!!data.provenance.rows?.length && (
                  <div className="dd-prov-rows">
                    {data.provenance.rows.slice(0, 8).map((r: any) => (
                      <div className="dd-prov-row" key={r.ticker}>
                        <span>{r.name}</span>
                        <span className="tiny">
                          {r.close ? `₹${r.close.toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "—"}
                          {r.as_of ? ` as of ${r.as_of}` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="dd-clock">
                  Simulation clock: {String(data.provenance.clock).slice(0, 10)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

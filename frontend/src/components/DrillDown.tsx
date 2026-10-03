import { useT } from "../lib/i18n";
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
  const { t } = useT();
  return (
    <span className={`num-drill ${className}`} title={t("Where does this number come from?", "यह आँकड़ा कहाँ से आता है?")}
          onClick={(e) => { e.stopPropagation(); openDrill(metric, k); }}>
      {value}
    </span>
  );
}

export function DrillDown() {
  const { hi, t, d } = useT();
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
        {!data && <div className="dd-load">{t("opening…", "खुल रहा है…")}</div>}
        {data?.error && <div className="dd-load">{data.error}</div>}

        {data && !data.error && (
          <>
            <div className="dd-top">
              <div>
                <div className="dd-title">{d(data.title)}</div>
                <div className="dd-value">
                  {data.display}
                  {data.limit_display && (
                    <span className={`dd-limit ${data.over_by > 0 ? "over" : ""}`}>
                      {t("limit", "सीमा")} {data.limit_display}
                      {data.over_by > 0 && ` · ${t("over by", "इतना ऊपर")} ${pct(data.over_by)}`}
                    </span>
                  )}
                </div>
              </div>
              <button className="flow-x" onClick={close}>✕</button>
            </div>

            {!!data.components?.length && (
              <div className="dd-section">
                <div className="dd-label">{t("What it is made of", "यह किससे बना है")}</div>
                {data.components.map((c: any, i: number) => (
                  <div className="dd-comp" key={i}>
                    <div className="dd-comp-main">
                      <span className="dd-comp-label">{d(c.label)}</span>
                      <span className="dd-comp-value">
                        {typeof c.value === "number" && Math.abs(c.value) > 999
                          ? rupees(c.value)
                          : typeof c.value === "number" && Math.abs(c.value) <= 1 && c.value !== 0
                            ? pct(c.value)
                            : c.value}
                      </span>
                    </div>
                    {c.sub && <div className="dd-comp-sub">{d(c.sub)}</div>}
                  </div>
                ))}
              </div>
            )}

            <div className="dd-section">
              <div className="dd-label">{t("How it was worked out", "यह कैसे निकाला गया")}</div>
              <div className="dd-formula">{d(data.formula)}</div>
            </div>

            <div className="dd-section">
              <div className="dd-label">{t("Why it matters", "यह क्यों मायने रखता है")}</div>
              <div className="dd-why">{d(data.why)}</div>
            </div>

            {data.provenance && (
              <div className="dd-prov">
                <div className="dd-label">
                  {t("Where it came from", "यह कहाँ से आया")}
                  <span className={`dd-tier t-${data.provenance.tier}`}>
                    {data.provenance.tier}
                  </span>
                </div>
                <div className="dd-prov-rule">{d(data.provenance.rule)}</div>
                {!!data.provenance.rows?.length && (
                  <div className="dd-prov-rows">
                    {data.provenance.rows.slice(0, 8).map((r: any) => (
                      <div className="dd-prov-row" key={r.ticker}>
                        <span>{r.name}</span>
                        <span className="tiny">
                          {r.close ? `₹${r.close.toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "—"}
                          {r.as_of ? ` ${t("as of", "तक")} ${r.as_of}` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="dd-clock">
                  {t("Simulation clock", "सिमुलेशन की घड़ी")}: {String(data.provenance.clock).slice(0, 10)}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

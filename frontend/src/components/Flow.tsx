import { useT } from "../lib/i18n";
import { useEffect, useState } from "react";

import { chooseOption, useGuide } from "../lib/guide";
import { pct, rupees } from "./Portfolio";

/** The flow runner: one beat at a time, with the numbers for that beat beside it.
 *
 *  The design rule this enforces is that a flow never tells you to go and look
 *  somewhere. Each step raises its own panel and fetches its own data, so the app is
 *  doing the navigating. That is the whole difference between guiding and being guided. */
export function FlowRunner() {
  const { t } = useT();
  const flow = useGuide((s) => s.flow);
  const index = useGuide((s) => s.step);
  const data = useGuide((s) => s.stepData);
  const busy = useGuide((s) => s.stepBusy);
  const guided = useGuide((s) => s.guidedVoice);
  const next = useGuide((s) => s.next);
  const back = useGuide((s) => s.back);
  const end = useGuide((s) => s.endFlow);
  const setGuided = useGuide((s) => s.setGuidedVoice);

  // Enter advances, Escape leaves. A guided sequence people cannot drive from the
  // keyboard becomes a sequence they click through while reading nothing.
  useEffect(() => {
    if (!flow) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "Escape") { e.preventDefault(); end(); }
      if (e.key === "Enter" || e.key === "ArrowRight") { e.preventDefault(); void next(); }
      if (e.key === "ArrowLeft") { e.preventDefault(); void back(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flow, next, back, end]);

  if (!flow?.steps?.length) return null;
  const step = flow.steps[index];
  const last = index === flow.steps.length - 1;

  return (
    <div className="flow-wrap">
      <div className="flow-card">
        <div className="flow-top">
          <div className="flow-name">{flow.title}</div>
          <div className="flow-pips">
            {flow.steps.map((_, i) => (
              <span key={i} className={`fp ${i === index ? "on" : i < index ? "done" : ""}`} />
            ))}
          </div>
          <button className="flow-x" onClick={end} title={t("Leave (Esc)", "छोड़ें (Esc)")}>✕</button>
        </div>

        <div className="flow-body">
          <div className="flow-say">{step.text}</div>
          {step.note && <div className="flow-note">{step.note}</div>}

          {busy && <div className="flow-load">{t("working…", "काम हो रहा है…")}</div>}
          {!busy && <StepData kind={step.kind} data={data} />}

          {step.kind === "choose" && (
            <div className="flow-opts">
              {step.options.map((o) => (
                <div className="flow-opt" key={o.key}
                     onClick={() => void chooseOption(o.endpoint)}>
                  <div className="fo-label">{o.label}</div>
                  <div className="fo-conseq">{o.consequence}</div>
                </div>
              ))}
            </div>
          )}

          {step.kind === "confirm" && <ConfirmStep />}
        </div>

        <div className="flow-foot">
          <label className="flow-voice">
            <input type="checkbox" checked={guided}
                   onChange={(e) => setGuided(e.target.checked)} />
            {t("read aloud", "ज़ोर से पढ़ें")}
          </label>
          <div className="flow-nav">
            <span className="flow-count">{index + 1} / {flow.steps.length}</span>
            {index > 0 && <button className="btn sm ghost" onClick={() => void back()}>{t("Back", "पीछे")}</button>}
            {step.kind !== "choose" && (
              <button className="btn go sm" onClick={() => void next()}>
                {last ? t("Done", "हो गया") : t("Next", "आगे")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Whatever this beat fetched, rendered in the shape it actually is. */
function StepData({ kind, data }: { kind: string; data: any }) {
  const { hi, t } = useT();
  if (!data) return null;

  // An answer from the explainer.
  if (kind === "ask" && data.headline) {
    return (
      <div className="flow-answer">
        <div className="fa-head">{data.headline}</div>
        {data.bullets?.slice(0, 3).map((b: string, i: number) => (
          <div className="fa-bullet" key={i}>{b}</div>
        ))}
        {data.action && <div className="fa-action">{data.action}</div>}
      </div>
    );
  }

  // The X-ray.
  if (data.grade && data.score != null) {
    return (
      <div className="flow-data">
        <div className="fd-score">
          <span className={`grade g${data.grade}`}>{data.grade}</span>
          <span className="fd-num">{data.score}<i>/100</i></span>
          <span className="fd-meta">{data.holdings} {t("holdings", "शेयर")} · {data.sectors} {t("industries", "उद्योग")}</span>
        </div>
        {data.findings?.slice(0, 3).map((f: any, i: number) => (
          <div className={`fd-find ${f.severity}`} key={i}>{f.headline}</div>
        ))}
      </div>
    );
  }

  // Stress scenarios.
  if (data.scenarios?.length) {
    return (
      <div className="flow-data">
        {data.scenarios.slice(0, 5).map((s: any) => (
          <div className="fd-row" key={s.key}>
            <span>{hi ? SCENARIO_HI[s.key] ?? s.label : s.label}</span>
            <span style={{ color: s.portfolio_return < 0 ? "var(--red)" : "var(--green)" }}>
              {pct(s.portfolio_return)}
            </span>
          </div>
        ))}
      </div>
    );
  }

  // A rebalance plan.
  if (data.trades?.length) {
    return (
      <div className="flow-data">
        {data.trades.slice(0, 6).map((t: any, i: number) => (
          <div className="fd-row" key={i}>
            <span><b className={t.side === "SELL" ? "sell" : "buy"}>{hi ? (t.side === "SELL" ? "बेचें" : "ख़रीदें") : t.side}</b>{" "}
              {t.shares} {t.name}</span>
            <span>{rupees(t.value ?? 0)}</span>
          </div>
        ))}
        {data.tax?.total_tax > 0 && (
          <div className="fd-note">{t("Tax on this plan", "इस योजना पर टैक्स")}: {rupees(data.tax.total_tax)}</div>
        )}
      </div>
    );
  }

  // Correlated pairs.
  if (data.pairs?.length) {
    return (
      <div className="flow-data">
        {data.pairs.slice(0, 4).map((p: any, i: number) => (
          <div className="fd-row" key={i}>
            <span>{p.a_name} / {p.b_name}</span>
            <span>{p.correlation.toFixed(2)}</span>
          </div>
        ))}
      </div>
    );
  }

  // Screener results.
  if (data.results?.length) {
    return (
      <div className="flow-data">
        {data.results.slice(0, 5).map((r: any, i: number) => (
          <div className="fd-row" key={i}>
            <span>{r.name}</span>
            <span className="tiny">{r.reason ?? ""}</span>
          </div>
        ))}
      </div>
    );
  }

  // Missing cost basis.
  if (data.missing?.length || data.lots) {
    return (
      <div className="flow-data">
        {(data.missing ?? []).slice(0, 6).map((m: any, i: number) => (
          <div className="fd-row" key={i}>
            <span>{m.name}</span><span className="tiny">{t("no purchase price", "ख़रीद भाव दर्ज नहीं")}</span>
          </div>
        ))}
        {!data.missing?.length && (
          <div className="fd-note">{t("Every holding has a purchase price on file.", "हर शेयर का ख़रीद भाव दर्ज है।")}</div>
        )}
      </div>
    );
  }

  return null;
}

/** The staging step: commit nothing, show what it would do. */
function ConfirmStep() {
  const { hi, t } = useT();
  const next = useGuide((s) => s.next);
  const [state, setState] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const stage = async () => {
    setBusy(true);
    try {
      const res = await fetch("/sandbox/from-rebalance", { method: "POST" });
      setState(await res.json());
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flow-confirm">
      {!state && (
        <button className="btn go" disabled={busy} onClick={() => void stage()}>
          {busy ? t("working…", "काम हो रहा है…") : t("Stage it and show me the difference", "इसे रखिए और फ़र्क़ दिखाइए")}
        </button>
      )}
      {state && !state.staged && (
        <div className="fc-small">{t("Nothing needed staging — you are already inside every limit.", "रखने को कुछ नहीं था — आप पहले से हर सीमा के भीतर हैं।")}</div>
      )}
      {state?.staged && (
        <>
          <div className="fc-verdict">{hi ? verdictHi(state.verdict) : state.verdict}</div>
          <div className="fc-deltas">
            {state.deltas.slice(0, 5).map((d: any) => (
              <div className={`fc-delta ${d.direction}`} key={d.key}>
                <span>{hi ? DELTA_HI[d.label] ?? d.label : d.label}</span>
                <span>{fmt(d.before, d.format)} → {fmt(d.after, d.format)}</span>
              </div>
            ))}
          </div>
          <div className="fc-buttons">
            <button className="btn go sm" onClick={async () => {
              await fetch("/sandbox/commit", { method: "POST" });
              void next();
            }}>{t("Commit it", "पक्का करें")}</button>
            <button className="btn sm ghost" onClick={async () => {
              await fetch("/sandbox/discard", { method: "POST" });
              void next();
            }}>{t("Throw it away", "हटा दें")}</button>
          </div>
          <div className="fc-small">
            {t("Nothing has moved yet. Committing runs each trade through the same risk firewall a spoken order hits.", "अभी कुछ नहीं हिला है। पक्का करने पर हर सौदा उसी जोखिम की दीवार से गुज़रता है जिससे बोलकर दिया गया आदेश गुज़रता है।")}
          </div>
        </>
      )}
    </div>
  );
}

const SCENARIO_HI: Record<string, string> = {
  covid: "कोविड की गिरावट", covid_recovery: "कोविड के बाद की रिकवरी", rate_shock_2022: "2022 की ब्याज दरों की मार",
  adani_2023: "जनवरी 2023 की बिकवाली", market_10: "बाज़ार 10% गिरे", market_20: "बाज़ार 20% गिरे",
  it_30: "टेक्नोलॉजी 30% गिरे", banks_25: "बैंक 25% गिरें",
};
const DELTA_HI: Record<string, string> = {
  Score: "स्कोर", Cash: "नक़द", "Behaves like": "असल में कितने शेयर", Holdings: "शेयर", Industries: "उद्योग",
  "Total value": "कुल क़ीमत", "Market sensitivity": "बाज़ार से संवेदनशीलता", "Breaches resolved": "सुलझी ख़ामियाँ", "New breaches": "नई ख़ामियाँ",
};
/** The four sentences the staging preview can return, in Hindi (the one figure is carried over). */
function verdictHi(v: string): string {
  const pts = v.match(/\d+/)?.[0];
  if (v.startsWith("This puts you inside")) return `इससे आप अपनी तय हर सीमा के भीतर आ जाते हैं, और स्कोर ${pts} अंक बढ़ता है।`;
  if (v.startsWith("Better on balance")) return `कुल मिलाकर बेहतर — ${pts} अंक — पर सब कुछ सुलझा नहीं है।`;
  if (v.startsWith("This is not an improvement")) return "जो आँकड़े मायने रखते हैं उन पर यह सुधार नहीं है। पक्का करने से पहले यह जान लेना ज़रूरी है।";
  if (v.startsWith("Roughly neutral")) return "लगभग बराबर। यहाँ मुख्य लागत सौदे करने की ही है।";
  return v;
}

function fmt(v: number, format: string): string {
  if (format === "pct") return pct(v);
  if (format === "money") return rupees(v);
  if (format === "x") return `${v}x`;
  if (format === "count") return Number(v).toFixed(1).replace(/\.0$/, "");
  return String(v);
}

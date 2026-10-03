import { useEffect, useState } from "react";

import { Panel } from "./Panels";
import { pct, rupees } from "./Portfolio";
import { useStore } from "../lib/store";
import { Num } from "./DrillDown";

/** Portfolio X-ray. The first screen a new user should see, because "what does what
 *  I already own look like" is the question they actually have. */
export function XRayPanel({ onOpenBuilder }: { onOpenBuilder: () => void }) {
  const [data, setData] = useState<any>(null);
  const fund = useStore((s) => s.fund);
  const simClock = useStore((s) => s.simClock);

  useEffect(() => {
    fetch("/xray").then((r) => r.json()).then(setData).catch(() => {});
  }, [fund?.nav, fund?.portfolio_id, fund?.policy?.profile, simClock]);

  if (!data) return null;
  if (data.empty) {
    return (
      <Panel title="Portfolio X-ray">
        <div className="empty">Nothing to analyse yet.</div>
        <button className="btn go" style={{ marginTop: 8 }} onClick={onOpenBuilder}>
          Add your holdings
        </button>
      </Panel>
    );
  }

  const tone = data.score >= 70 ? "ok" : data.score < 45 ? "alert" : undefined;
  return (
    <Panel title="Portfolio X-ray" tone={tone}>
      {/* Every figure below is a door: click it for the rows it is made of, the
          formula, and the prices it was computed from. */}
      <div className="score-row">
        <div className={`grade g${data.grade}`}>{data.grade}</div>
        <div className="score-meta">
          <div className="score-num">
            <Num metric="score" value={data.score} /><span>/100</span>
          </div>
          <div className="tiny">vs {data.profile_name?.toLowerCase()} limits</div>
        </div>
      </div>

      <div className="kv"><span className="k">Total value</span>
        <span className="v"><Num metric="nav" value={rupees(data.nav)} /></span></div>
      <div className="kv"><span className="k">Holdings</span>
        <span className="v">{data.holdings} in {data.sectors} industries</span></div>
      <div className="kv" title="How many positions you really have, once the big ones are accounted for">
        <span className="k">Behaves like</span>
        <span className="v">
          <Num metric="effective_holdings" value={`${data.effective_holdings} positions`} />
        </span></div>
      {data.top_sector && (
        <div className="kv"><span className="k">Biggest industry</span>
          <span className="v">
            <Num metric="sector" k={data.top_sector[0]}
                 value={pct(data.top_sector[1])} />
          </span></div>
      )}
      {data.max_drawdown != null && (
        <div className="kv" title="Worst peak-to-trough fall on the history we hold">
          <span className="k">Worst fall so far</span>
          <span className="v" style={{ color: "var(--red)" }}>
            <Num metric="max_drawdown" value={pct(Math.abs(data.max_drawdown))} />
          </span></div>
      )}
      {data.beta != null && (
        <div className="kv" title="How much you move when the market moves">
          <span className="k">Market sensitivity</span>
          <span className="v"><Num metric="beta" value={`${data.beta}x`} /></span></div>
      )}

      <div className="findings">
        {data.findings.map((f: any, i: number) => (
          <div className={`finding ${f.severity}`} key={i}>
            <div className="f-head">{f.headline}</div>
            <div className="f-detail">{f.detail}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

/** Stress tests. Historical windows are facts about your holdings; the parametric
 *  ones are labelled as what-ifs, and the UI keeps that distinction visible. */
export function StressPanel() {
  const [data, setData] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const fund = useStore((s) => s.fund);

  useEffect(() => {
    fetch("/stress").then((r) => r.json()).then(setData).catch(() => {});
  }, [fund?.nav, fund?.portfolio_id]);

  if (!data?.scenarios?.length) return null;
  const worst = data.worst_case;

  return (
    <Panel title="What if it goes wrong" tone={worst && worst.portfolio_return < -0.25 ? "alert" : undefined}>
      {worst && (
        <div className="worst-case">
          <div className="wc-label">Worst case tested</div>
          <div className="wc-value">{rupees(Math.abs(worst.value_change))}</div>
          <div className="wc-sub">
            lost in the {worst.label.toLowerCase()} — {pct(Math.abs(worst.portfolio_return))} of your money
          </div>
        </div>
      )}

      {data.scenarios.map((s: any) => (
        <div key={s.key}>
          <div className="scenario" onClick={() => setOpen(open === s.key ? null : s.key)}>
            <span className={`kind ${s.kind}`} title={
              s.kind === "historical"
                ? "Real prices from a window that actually happened"
                : "A what-if: the same fall applied uniformly"}>
              {s.kind === "historical" ? "REAL" : "WHAT-IF"}
            </span>
            <span className="s-label">{s.label}</span>
            <span className={`s-ret ${s.portfolio_return < 0 ? "neg" : "pos"}`}>
              {s.portfolio_return > 0 ? "+" : ""}{pct(s.portfolio_return)}
            </span>
          </div>
          {open === s.key && (
            <div className="scenario-detail">
              <div>{s.blurb}</div>
              <div className="kv"><span className="k">Your value</span>
                <span className="v">{rupees(s.nav_before)} → {rupees(s.nav_after)}</span></div>
              {s.benchmark_return != null && (
                <div className="kv"><span className="k">{data.benchmark_label}</span>
                  <span className="v">{pct(s.benchmark_return)}</span></div>
              )}
              {!!s.worst?.length && (
                <div className="kv"><span className="k">Hardest hit</span>
                  <span className="v">{s.worst.map((w: any) => w[0]).join(", ")}</span></div>
              )}
              {s.coverage < 0.95 && (
                <div className="tiny" style={{ marginTop: 5 }}>
                  Only {pct(s.coverage)} of your money could be priced in this window —
                  some holdings had not listed yet.
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </Panel>
  );
}

/** Plain-language Q&A. Suggested questions matter more than the input box: a user who
 *  does not know what to ask will ask nothing. */
const SUGGESTED = [
  "How am I doing?",
  "Why is my risk high?",
  "What should I sell?",
  "What if the market drops 20%?",
  "What happened in Covid?",
  "Am I diversified?",
];

export function AskPanel() {
  const [answer, setAnswer] = useState<any>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState<string>("");

  const ask = async (question: string, level: "normal" | "simple" | "maths" = "normal") => {
    if (!question.trim()) return;
    setBusy(true);
    if (level === "normal") { setQ(question); setAsked(question); }
    try {
      const res = await fetch("/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, level }),
      });
      setAnswer(await res.json());
      if (level === "normal") setQ("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Ask me anything">
      <div className="ask-chips">
        {SUGGESTED.map((s) => (
          <div className="ask-chip" key={s} onClick={() => ask(s)}>{s}</div>
        ))}
      </div>
      <div className="cmdrow" style={{ marginTop: 8 }}>
        <input className="field" placeholder="Ask in your own words…" value={q}
               onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => { if (e.key === "Enter") ask(q); }} />
        <button className="btn go" disabled={busy} onClick={() => ask(q)}>
          {busy ? "…" : "Ask"}
        </button>
      </div>

      {answer && (
        <div className="answer">
          <div className="a-head">{answer.headline}</div>
          {answer.bullets?.map((b: string, i: number) => (
            <div className="a-bullet" key={i}>{b}</div>
          ))}
          {answer.action && <div className="a-action">{answer.action}</div>}

          {/* Explain-back. Three levels of the same truth, the reader picks — rather
              than one level and a hope that it landed. */}
          <div className="a-levels">
            <span className="a-lv-label">Does that make sense?</span>
            <button className={`a-lv ${answer.level === "simple" ? "on" : ""}`}
                    disabled={busy} onClick={() => ask(asked, "simple")}>
              Simpler
            </button>
            <button className={`a-lv ${answer.level === "maths" ? "on" : ""}`}
                    disabled={busy} onClick={() => ask(asked, "maths")}>
              Show the maths
            </button>
            {answer.level !== "normal" && (
              <button className="a-lv" disabled={busy} onClick={() => ask(asked, "normal")}>
                Back
              </button>
            )}
          </div>

          {/* Next moves, derived from the answer that was just given. An answer with no
              exit leaves the user holding a fact and no idea what to do with it. */}
          {!!answer.follow_ups?.length && (
            <div className="a-next">
              <div className="a-next-label">Next</div>
              {answer.follow_ups.map((f: string, i: number) => (
                <div className="ask-chip next" key={f} onClick={() => ask(f)}>{answer.follow_ups_hi?.[i] ?? f}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

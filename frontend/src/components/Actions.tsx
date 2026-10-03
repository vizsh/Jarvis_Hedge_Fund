import { useEffect, useState } from "react";

import { Panel } from "./Panels";
import { useGuide, type Action, type Flow } from "../lib/guide";
import { useStore } from "../lib/store";
import { useT } from "../lib/i18n";

const rupees = (v: number) => {
  const a = Math.abs(v);
  if (a >= 1e7) return `₹${(a / 1e7).toFixed(2)} crore`;
  if (a >= 1e5) return `₹${(a / 1e5).toFixed(2)} lakh`;
  return `₹${Math.round(a).toLocaleString("en-IN")}`;
};

const MARK: Record<string, string> = {
  urgent: "!", important: "▲", opportunity: "◆", ok: "✓",
};

/** The panel that means nobody has to be guided.
 *
 *  Every other panel answers a question, which only helps someone who already knows
 *  which question to ask. This one proposes, ranked, with the fix attached to each row.
 *  It is the first thing on screen for exactly that reason. */
export function ActionQueue() {
  const [data, setData] = useState<{ actions: Action[]; count: number; hidden: number;
                                     clean: boolean; grade?: string; urgent?: number } | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const fund = useStore((s) => s.fund);
  const simClock = useStore((s) => s.simClock);
  const startFlow = useGuide((s) => s.startFlow);

  const load = () => fetch("/actions").then((r) => r.json()).then(setData).catch(() => {});
  useEffect(() => { load(); },
    [fund?.nav, fund?.portfolio_id, fund?.policy?.profile, simClock]);

  if (!data?.actions?.length) return null;

  const act = (a: Action) => {
    if (a.flow) { void startFlow(a.flow); return; }
    if (a.question) {
      void fetch("/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: a.question }),
      });
    }
  };

  const tone = data.urgent ? "alert" : data.clean ? "ok" : undefined;
  return (
    <Panel title="What to do next" tone={tone} className="action-queue">
      <div className="aq-sub">
        {data.clean
          ? "Nothing outside your limits right now."
          : `${data.count} thing${data.count === 1 ? "" : "s"} worth your attention, most important first.`}
      </div>

      {data.actions.map((a) => (
        <div className={`aq-row ${a.severity}`} key={a.id}>
          <div className="aq-head" onClick={() => setOpen(open === a.id ? null : a.id)}>
            <span className={`aq-mark ${a.severity}`}>{MARK[a.severity] ?? "•"}</span>
            <span className="aq-title">{a.title}</span>
            {a.deadline_label && <span className="aq-clock">{a.deadline_label}</span>}
          </div>
          <div className="aq-detail">{a.detail}</div>

          {open === a.id && (
            <div className="aq-why">
              <div className="aq-why-label">Why this matters</div>
              {a.why}
              {a.stake > 0 && (
                <div className="aq-stake">About {rupees(a.stake)} turns on this.</div>
              )}
            </div>
          )}

          <div className="aq-actions">
            <button className="btn go sm" onClick={() => act(a)}>{a.cta}</button>
            <button className="btn sm ghost"
                    onClick={() => setOpen(open === a.id ? null : a.id)}>
              {open === a.id ? "less" : "why?"}
            </button>
          </div>
        </div>
      ))}

      {!!data.hidden && (
        <div className="aq-more">{data.hidden} more, lower priority.</div>
      )}
    </Panel>
  );
}

/** Jobs, not modes.
 *
 *  "My money / Fund desk / Machinery" are audiences. People arrive with a job — check
 *  my health, fix the thing you flagged, get ready for tax season. Each tile runs a
 *  sequence that opens the right panels itself, so nobody has to be told where to look. */
export function JobsLauncher({ compact = false }: { compact?: boolean }) {
  const { hi, t } = useT();
  const [flows, setFlows] = useState<Flow[]>([]);
  const startFlow = useGuide((s) => s.startFlow);

  useEffect(() => {
    fetch(`/flows?lang=${hi ? "hi" : "en"}`).then((r) => r.json()).then((d) => setFlows(d.flows ?? []))
      .catch(() => {});
  }, [hi]);

  if (!flows.length) return null;
  const shown = compact ? flows.slice(0, 5) : flows;

  return (
    <Panel title={t("What do you want to do?", "आप क्या करना चाहते हैं?")} className="jobs">
      <div className="jobs-grid">
        {shown.map((f) => (
          <div className="job" key={f.id} onClick={() => void startFlow(f.id)}>
            <div className={`job-icon i-${f.icon}`} />
            <div className="job-body">
              <div className="job-title">{f.title}</div>
              <div className="job-sub">{f.subtitle}</div>
            </div>
            <div className="job-time">{f.minutes}{t("m", " मि")}</div>
          </div>
        ))}
      </div>
      <div className="jobs-foot">
        {t("Each one walks you through it and opens the panels for you. Press", "हर एक आपको क़दम-दर-क़दम समझाता है और पैनल खोल देता है। सब कुछ खोजने के लिए")}
        <kbd>Ctrl</kbd>+<kbd>K</kbd> {t("to search everything.", "दबाइए।")}
      </div>
    </Panel>
  );
}

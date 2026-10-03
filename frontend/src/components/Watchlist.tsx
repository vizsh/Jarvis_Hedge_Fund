import { useEffect, useState } from "react";

import { Panel } from "./Panels";
import { useStore } from "../lib/store";
import { useT } from "../lib/i18n";

interface Watch {
  id: string; label: string; metric: string; value: number | null;
  state: "ok" | "breached" | "unknown"; unit?: string; threshold: number;
}

interface Suggestion {
  metric: string; op: string; subject: string | null; threshold: number;
  label: string; because: string;
}

const show = (v: number | null, unit?: string) => {
  if (v == null) return "—";
  if (unit === "pct") return `${(v * 100).toFixed(1)}%`;
  if (unit === "count") return v.toFixed(1);
  return Math.round(v).toString();
};

/** Standing rules — the only part of this product that speaks without being asked.
 *
 *  Everything else is pull: you ask, it answers, which makes it a thing you open when
 *  you already suspect something. A watch is push. You say once what would worry you
 *  and it checks itself every time the book moves. */
export function WatchlistPanel() {
  const { t, d } = useT();
  const [data, setData] = useState<{ watches: Watch[]; breached: Watch[];
                                     suggestions?: Suggestion[] } | null>(null);
  const [adding, setAdding] = useState(false);
  const fund = useStore((s) => s.fund);
  const simClock = useStore((s) => s.simClock);

  const load = () => fetch("/watch").then((r) => r.json()).then(setData).catch(() => {});
  useEffect(() => { load(); }, [fund?.nav, fund?.portfolio_id, simClock]);

  const add = async (s: Suggestion) => {
    await fetch("/watch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metric: s.metric, op: s.op, threshold: s.threshold,
                             subject: s.subject }),
    });
    setAdding(false);
    load();
  };

  const drop = async (id: string) => {
    await fetch(`/watch/${id}`, { method: "DELETE" });
    load();
  };

  if (!data) return null;
  const breached = data.breached?.length ?? 0;

  return (
    <Panel title={t("Tell me if…", "मुझे बताइए अगर…")} tone={breached ? "alert" : undefined} className="watchlist">
      {!data.watches.length && (
        <div className="wl-empty">
          {t("No standing rules yet. Set one and I will check it every time your portfolio moves, without you having to ask.", "अभी कोई स्थायी नियम नहीं है। एक बनाइए, मैं हर बार आपका पोर्टफ़ोलियो हिलने पर उसे बिना पूछे जाँचूँगा।")}
        </div>
      )}

      {data.watches.map((w) => (
        <div className={`wl-row ${w.state}`} key={w.id}>
          <div className="wl-main">
            <span className={`wl-dot ${w.state}`} />
            <span className="wl-label">{d(w.label)}</span>
          </div>
          <div className="wl-side">
            <span className="wl-value">{show(w.value, w.unit)}</span>
            <button className="wl-x" title={t("Remove", "हटाइए")} onClick={() => drop(w.id)}>✕</button>
          </div>
        </div>
      ))}

      {(adding || !data.watches.length) && !!data.suggestions?.length && (
        <div className="wl-suggest">
          <div className="wl-sug-label">{t("Worth watching, based on where you are today", "आज आप जहाँ हैं, उसके हिसाब से नज़र रखने लायक़")}</div>
          {data.suggestions.map((s, i) => (
            <div className="wl-sug" key={i} onClick={() => void add(s)}>
              <div className="wl-sug-text">{d(s.label)}</div>
              <div className="wl-sug-why">{d(s.because)}</div>
            </div>
          ))}
        </div>
      )}

      {!!data.watches.length && (
        <button className="btn sm ghost wl-add" onClick={() => setAdding(!adding)}>
          {adding ? t("close", "बंद करें") : t("+ add a rule", "+ नियम जोड़ें")}
        </button>
      )}

      {adding && !data.suggestions?.length && (
        <SuggestionLoader onPick={add} />
      )}
    </Panel>
  );
}

/** Suggestions only come back when the list is empty, so fetch them explicitly once
 *  somebody asks to add a second rule. */
function SuggestionLoader({ onPick }: { onPick: (s: Suggestion) => void }) {
  const { d } = useT();
  const [sugs, setSugs] = useState<Suggestion[]>([]);

  useEffect(() => {
    fetch("/xray").then((r) => r.json()).then((x) => {
      if (x.empty) return;
      const out: Suggestion[] = [];
      if (x.top_sector) {
        const [code, w] = x.top_sector;
        out.push({ metric: "sector_weight", op: "above", subject: code,
                   threshold: Math.min(0.95, Number(w) + 0.05),
                   label: `Tell me if that industry goes above ${((Number(w) + 0.05) * 100).toFixed(0)}%`,
                   because: `You are at ${(Number(w) * 100).toFixed(0)}% today.` });
      }
      out.push({ metric: "cash_pct", op: "below", subject: null, threshold: 0.05,
                 label: "Tell me if my cash buffer goes below 5%",
                 because: "A thin buffer forces you to sell to buy." });
      out.push({ metric: "worst_case_loss", op: "above", subject: null, threshold: 0.3,
                 label: "Tell me if my worst tested loss goes above 30%",
                 because: "Recomputed as your holdings change." });
      setSugs(out);
    }).catch(() => {});
  }, []);

  return (
    <div className="wl-suggest">
      {sugs.map((s, i) => (
        <div className="wl-sug" key={i} onClick={() => onPick(s)}>
          <div className="wl-sug-text">{d(s.label)}</div>
          <div className="wl-sug-why">{d(s.because)}</div>
        </div>
      ))}
    </div>
  );
}

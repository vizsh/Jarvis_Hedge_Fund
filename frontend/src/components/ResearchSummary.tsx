import { useEffect, useState } from "react";

import "../styles-summary.css";
import { useT } from "../lib/i18n";
import { useLang } from "../lib/lang";
import { speak } from "../lib/speak";
import { useStore } from "../lib/store";

type Item = { title: string; why: string; tag?: string; confidence?: "solid" | "light" | "weak"; basis?: string };
type Rank = { metric: string; value: string; rank: number; of: number };
type Fresh = { label: string; date: string | null; age_days: number | null };
type Sum = { name: string; about: string; pros: Item[]; cons: Item[]; gaps: string[]; for_you: string[]; how_to_read: string[]; ranks?: Rank[]; freshness?: Fresh[]; coverage?: { ran: number; of: number } };

/** The research result in plain words: what looks good, what to watch, what could not be checked. No buy or sell signal. */
export function ResearchSummary() {
  const { t } = useT();
  const lang = useLang((s) => s.lang);
  const ticker = useStore((s) => s.ticker);
  const [d, setD] = useState<Sum | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    setErr(false);
    fetch(`/research/summary?ticker=${encodeURIComponent(ticker)}&lang=${lang}`)
      .then((r) => r.json()).then((x) => { if (alive) setD(x); }).catch(() => { if (alive) setErr(true); });
    return () => { alive = false; };
  }, [ticker, lang]);

  if (err) return <section className="card"><p className="muted">{t("Could not load the summary. Is the backend running?", "सारांश नहीं ला सका। क्या बैकएंड चल रहा है?")}</p></section>;
  if (!d) return <section className="card"><p className="muted">{t("Reading the numbers…", "आँकड़े पढ़ रहा हूँ…")}</p></section>;

  const say = () => speak([d.about,
    ...(d.pros.length ? [t("Good points: ", "अच्छी बातें: ") + d.pros.map((x) => x.title).join(". ")] : []),
    ...(d.cons.length ? [t("Things to watch: ", "ध्यान देने की बातें: ") + d.cons.map((x) => x.title).join(". ")] : []),
    d.how_to_read[1]].join(" "), lang === "hi" ? "hi" : "en", true);
  const CONF = { solid: t("Solid basis", "पक्का आधार"), light: t("Light basis", "हल्का आधार"), weak: t("Weak basis", "कमज़ोर आधार") };
  const age = (a: number | null) => (a == null ? t("not saved", "सहेजा नहीं") : a === 0 ? t("today", "आज") : a === 1 ? t("1 day old", "1 दिन पुराना") : t(`${a} days old`, `${a} दिन पुराना`));
  const list = (items: Item[], empty: string) => items.length
    ? <ul>{items.map((x) => <li key={x.title}>{x.tag && <i className="sum-tag">{x.tag}</i>}{x.confidence && <i className={`sum-conf ${x.confidence}`} title={x.basis}>{CONF[x.confidence]}</i>}<b>{x.title}</b><span>{x.why}</span>{x.basis && <small className="sum-basis">{t("Based on: ", "आधार: ")}{x.basis}</small>}</li>)}</ul>
    : <p className="sum-none">{empty}</p>;

  return (
    <section className="card sum">
      <header className="sum-head">
        <div><h2>{t("In plain words:", "सरल शब्दों में:")} {d.name}</h2><p className="sum-about">{d.about}</p></div>
        <button className="btn ghost sm" onClick={say}>🔊 {t("Read aloud", "सुनें")}</button>
      </header>
      <div className="sum-cols">
        <div className="sum-col good"><h3>✓ {t("Good points", "अच्छी बातें")} <small>({d.pros.length})</small></h3>
          {list(d.pros, t("Nothing stands out as especially good in the numbers we hold.", "हमारे पास के आँकड़ों में कुछ ख़ास अच्छा नहीं दिखता।"))}</div>
        <div className="sum-col watch"><h3>⚠ {t("Things to watch", "ध्यान देने की बातें")} <small>({d.cons.length})</small></h3>
          {list(d.cons, t("Nothing stands out as a concern in the numbers we hold.", "हमारे पास के आँकड़ों में कोई चिंता की बात नहीं दिखती।"))}</div>
      </div>
      {d.ranks && d.ranks.length > 0 && <div className="sum-ranks"><h3>{t("Against similar companies", "समान कंपनियों के मुक़ाबले")}</h3>
        {d.ranks.map((r) => <div key={r.metric} className="sum-rank"><span>{r.metric}</span><b>{r.value}</b>
          <div className="sum-bar" role="img" aria-label={`${r.rank} / ${r.of}`}><i style={{ left: `${r.of > 1 ? ((r.rank - 1) / (r.of - 1)) * 100 : 50}%` }} /></div>
          <em>{t(`${r.rank} of ${r.of}`, `${r.of} में ${r.rank}वाँ`)}</em></div>)}
        <p className="sum-hint">{t("Left is the best of the group, right is the weakest.", "बाएँ समूह में सबसे अच्छी, दाएँ सबसे कमज़ोर।")}</p></div>}
      {d.freshness && <div className="sum-fresh"><h3>{t("How current is this?", "यह कितना ताज़ा है?")}{d.coverage && <small> · {t(`${d.coverage.ran} of ${d.coverage.of} checks had data`, `${d.coverage.of} में से ${d.coverage.ran} जाँचों के लिए डेटा था`)}</small>}</h3>
        <ul>{d.freshness.map((f) => <li key={f.label} className={f.age_days == null ? "none" : f.age_days > 45 ? "old" : ""}><span>{f.label}</span><b>{age(f.age_days)}</b></li>)}</ul></div>}
      {d.for_you.length > 0 && <div className="sum-you"><h3>{t("How it sits with what you already own", "आपके मौजूदा निवेश के साथ यह कैसा बैठता है")}</h3>{d.for_you.map((x) => <p key={x}>{x}</p>)}</div>}
      <details className="sum-gaps"><summary>{t("What we could not check", "जो हम जाँच नहीं सके")} ({d.gaps.length})</summary><ul>{d.gaps.map((g) => <li key={g}>{g}</li>)}</ul></details>
      <div className="sum-note">{d.how_to_read.map((x) => <p key={x}>{x}</p>)}</div>
    </section>
  );
}

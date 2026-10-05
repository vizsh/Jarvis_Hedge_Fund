import { TamperDemo } from "./Demos";
import { useEffect, useState } from "react";

import { Page } from "./Page";
import { GovernHero } from "../components/govern/GovernHero";
import { useStore } from "../lib/store";
import { useT } from "../lib/i18n";

const LEDGER_REASON_HI: Record<string, string> = { "rebalance plan": "संतुलन योजना", "sandbox commit": "रखे गए सौदे पक्के किए", "compliant counter-offer": "सीमा के भीतर वाला जवाबी प्रस्ताव" };

const inr = (v: number) => `₹${Math.round(Math.abs(v)).toLocaleString("en-IN")}`;
const pc = (v: number) => `${(v * 100).toFixed(1)}%`;
const post = (url: string, body?: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
               body: body === undefined ? undefined : JSON.stringify(body) });

/* ------------------------------------------------------------ firewall */
function Firewall({ onStage }: { onStage: () => void }) {
  const { hi, t, d } = useT();
  const [f, setF] = useState({ side: "BUY", ticker: "Persistent", shares: "30" });
  const [res, setRes] = useState<any>(null);

  const check = async (shares = f.shares, side = f.side, ticker = f.ticker) => {
    const r = await post("/firewall/check", { ticker, side, shares: Number(shares) });
    setRes(await r.json());
  };
  const stageRemedy = async () => {
    await post("/sandbox/stage", {
      origin: "firewall", note: "Largest size the firewall would approve",
      trades: [{ ticker: res.ticker, side: res.side, shares: res.remedy.max_shares, reason: "compliant counter-offer" }],
    });
    onStage();
  };

  return (
    <section className="card">
      <h2>{t("Risk firewall", "जोखिम की दीवार")}</h2>
      <p className="muted">{t("Try to place a trade. Plain arithmetic checks it against your limits — no AI is involved, so nothing can talk it into a bad order.", "कोई सौदा देकर देखिए। सीधा गणित उसे आपकी सीमाओं से जाँचता है — इसमें कोई AI नहीं है, इसलिए कोई उसे बुरा आदेश मानने के लिए मना नहीं सकता।")}</p>
      <div className="row">
        <select id="fw-side" value={f.side} onChange={(e) => setF({ ...f, side: e.target.value })}>
          <option value="BUY">{t("BUY", "ख़रीदें")}</option><option value="SELL">{t("SELL", "बेचें")}</option>
        </select>
        <input id="fw-shares" type="number" min={1} value={f.shares} style={{ width: 90 }}
               onChange={(e) => setF({ ...f, shares: e.target.value })} />
        <span className="muted">{t("shares of", "शेयर")}</span>
        <input id="fw-ticker" value={f.ticker} placeholder={t("company", "कंपनी")} style={{ flex: 1, minWidth: 120 }}
               onChange={(e) => setF({ ...f, ticker: e.target.value })} />
        <button className="btn go" onClick={() => check()}>{t("Check", "जाँचें")}</button>
      </div>
      <div className="row">
        <span className="faint small">{t("Try:", "आज़माइए:")}</span>
        {[["BUY", "Persistent", "30"], ["BUY", "TCS", "5"], ["SELL", "TCS", "9999"], ["BUY", "Nestle India", "10"]].map(([s, t, n]) => (
          <button key={t + n} className="chip" onClick={() => { setF({ side: s, ticker: t, shares: n }); void check(n, s, t); }}>
            {hi ? `${s === "BUY" ? "ख़रीदें" : "बेचें"} ${n} ${t}` : `${s.toLowerCase()} ${n} ${t}`}
          </button>
        ))}
      </div>

      {res && !res.ok && <p className="muted">{d(res.reason)}</p>}
      {res?.ok && (
        <div className={`fw-result ${res.approved ? "ok" : "no"}`}>
          <div className="fw-badge">{res.approved ? t("APPROVED", "मंज़ूर") : t("BLOCKED", "रोका गया")}</div>
          <div className="fw-line">{hi ? (res.side === "BUY" ? "ख़रीदें" : "बेचें") : res.side} {res.shares} × {res.name} at ₹{res.price.toLocaleString("en-IN")} = {inr(res.value)}</div>
          {res.violations.map((v: any, i: number) => (
            <div className="fw-viol" key={i}>
              <div>{d(v.message)}</div>
              <div className="faint small">
                {t("measured", "मापा गया")} {typeof v.measured === "number" && v.measured < 5 ? pc(v.measured) : v.measured}
                {" · "}{t("limit", "सीमा")} {typeof v.limit === "number" && v.limit < 5 ? pc(v.limit) : v.limit}
              </div>
            </div>
          ))}
          {res.approved && <div className="muted small">{t("Within every limit", "हर सीमा के भीतर")}: {d(res.policy)}.</div>}
          {!res.approved && res.remedy && res.remedy.max_shares > 0 && (
            <div className="fw-remedy">
              <div>{t("Largest order that fits your limits", "आपकी सीमाओं में बैठने वाला सबसे बड़ा आदेश")}: <b>{res.remedy.max_shares} {t("shares", "शेयर")}</b>.</div>
              <div className="faint small">{d(res.remedy.explanation)}</div>
              <div className="row">
                <button className="btn" onClick={() => check(String(res.remedy.max_shares))}>{t("Check that size", "वह आकार जाँचें")}</button>
                <button className="btn go" onClick={stageRemedy}>{t("Preview it in the simulator ↓", "सिमुलेटर में देखें ↓")}</button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ rebalance simulator */
const FIELDS: [string, string, string, (v: any, hi: boolean) => string][] = [
  ["score", "Score", "स्कोर", (v) => String(Math.round(v))],
  ["grade", "Grade", "ग्रेड", (v) => String(v)],
  ["cash_pct", "Cash", "नक़द", pc],
  ["effective_holdings", "Behaves like", "असल में कितने शेयर", (v, hi) => `${Number(v).toFixed(1)} ${hi ? "शेयर" : "stocks"}`],
  ["holdings", "Holdings", "शेयर", (v) => String(v)],
];

function RebalanceSim({ refreshKey, onBooked }: { refreshKey: number; onBooked: () => void }) {
  const { hi, t, d } = useT();
  const [p, setP] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<any>(null);
  const fund = useStore((s) => s.fund);

  const loadStaged = () => fetch("/sandbox").then((r) => r.json()).then((j) => setP(j.staged ? j : null)).catch(() => {});
  useEffect(() => { void loadStaged(); }, [refreshKey, fund?.nav]);

  const build = async (deploy: boolean) => {
    setBusy(true);
    try {
      const j = await (await post(`/sandbox/from-rebalance?deploy=${deploy}`)).json();
      setP(j.staged ? j : { staged: false });
    } finally { setBusy(false); }
  };
  const discard = async () => { await post("/sandbox/discard"); setP(null); };
  const approve = async () => {
    setBusy(true);
    try {
      setDone(await (await post("/sandbox/commit")).json());
      setP(null);
      onBooked();
    } finally { setBusy(false); }
  };

  const col = (title: string, s: any, deltas?: any[]) => (
    <div className={`sim-col ${deltas ? "after" : ""}`}>
      <h3>{title}</h3>
      {FIELDS.map(([k, l, lh, f]) => {
        const dd = deltas?.find((x) => x.key === k);
        return <div className="kvr" key={k}><span>{hi ? lh : l}</span><b className={dd ? dd.direction : ""}>{f(s[k], hi)}</b></div>;
      })}
      <div className="kvr"><span>{t("Biggest industry", "सबसे बड़ा उद्योग")}</span><b>{s.top_sector ? pc(s.top_sector[1]) : "—"}</b></div>
    </div>
  );

  return (
    <section className="card">
      <h2>{t("Rebalance simulator", "संतुलन सिमुलेटर")}</h2>
      <p className="muted">{t("See your portfolio now next to what it would become — before anything is booked. Nothing here is real money: this is paper trading.", "अपना पोर्टफ़ोलियो अभी और बदलने के बाद साथ-साथ देखिए — कुछ भी दर्ज होने से पहले। यहाँ असली पैसा नहीं है: यह अभ्यास वाला सौदा है।")}</p>
      {!p && (
        <div className="row">
          <button className="btn go" disabled={busy} onClick={() => build(true)}>{t("Build the smallest fix", "सबसे छोटा सुधार बनाइए")}</button>
          <button className="btn" disabled={busy} onClick={() => build(false)}>{t("Only sell, don't buy", "सिर्फ़ बेचिए, ख़रीदिए नहीं")}</button>
        </div>
      )}
      {p && p.staged === false && <p className="muted">{t("Nothing to change — you are already inside every limit.", "बदलने को कुछ नहीं — आप पहले से हर सीमा के भीतर हैं।")}</p>}
      {p?.staged && (
        <>
          <div className="sim">
            {col(t("Now", "अभी"), p.before)}
            <div className="sim-mid">
              {p.trades.map((tr: any, i: number) => (
                <div className={`xfer ${tr.side}`} key={i}>
                  <b>{hi ? (tr.side === "SELL" ? "बेचें" : "ख़रीदें") : tr.side}</b> {tr.shares} {tr.name}<span>{inr(tr.value)}</span>
                </div>
              ))}
              <div className="faint small">{t("Trading cost about", "सौदों की लागत लगभग")} {inr(p.cost)}</div>
            </div>
            {col(t("After", "बाद में"), p.after, p.deltas)}
          </div>
          <p className="verdict-line">{d(p.verdict)}</p>
          {!!p.skipped?.length && <p className="faint small">{t("Skipped", "छोड़े गए")}: {p.skipped.map((x: string) => d(x)).join("; ")}</p>}
          <div className="row">
            <button className="btn go" disabled={busy} onClick={approve}>{t("Approve and book on paper", "मंज़ूर करें और काग़ज़ पर दर्ज करें")}</button>
            <button className="btn ghost" disabled={busy} onClick={discard}>{t("Throw it away", "हटा दें")}</button>
          </div>
          <p className="faint small">{t("Approving re-checks every trade against the firewall and writes it to the ledger.", "मंज़ूर करने पर हर सौदा फिर दीवार से जाँचा जाता है और खाता-बही में लिखा जाता है।")}</p>
        </>
      )}

      {done && (
        <div className="modal-wrap" onClick={() => setDone(null)}>
          <div className="ok-modal" onClick={(e) => e.stopPropagation()}>
            <svg className="check" viewBox="0 0 52 52" aria-hidden="true">
              <circle className="check-c" cx="26" cy="26" r="23" fill="none" />
              <path className="check-p" fill="none" d="M14 27 l8 8 l16 -17" />
            </svg>
            <h3>{hi ? `${done.applied_count} सौदे काग़ज़ पर दर्ज हुए` : `${done.applied_count} trade${done.applied_count === 1 ? "" : "s"} booked on paper`}</h3>
            {done.applied?.map((tt: any, i: number) => (
              <div className="small" key={i}>{hi ? (tt.side === "SELL" ? "बेचें" : "ख़रीदें") : tt.side} {tt.shares} {tt.ticker?.replace(".NS", "")} · {inr(tt.value)}</div>
            ))}
            {!!done.refused_count && <p className="small neg">{hi ? `${done.refused_count} को दीवार ने मना किया।` : `${done.refused_count} refused by the firewall.`}</p>}
            <p className="faint small">{t("Written to the append-only ledger.", "केवल-जोड़ने वाली खाता-बही में लिखा गया।")}</p>
            <button className="btn go" onClick={() => setDone(null)}>{t("Done", "हो गया")}</button>
          </div>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------ ledger */
function Ledger({ refreshKey }: { refreshKey: number }) {
  const { hi, t, d: dt } = useT();
  const [d, setD] = useState<any>(null);
  const load = () => fetch("/ledger").then((r) => r.json()).then(setD).catch(() => {});
  useEffect(() => { void load(); }, [refreshKey]);
  if (!d) return null;
  return (
    <section className="card">
      <h2>{t("Audit ledger", "ऑडिट खाता-बही")}</h2>
      <p className="muted">{t("Every booked trade, in order. Each entry carries the fingerprint of the one before it, so editing history anywhere breaks the chain and shows up here.", "हर दर्ज सौदा, क्रम से। हर प्रविष्टि पिछली का फ़िंगरप्रिंट रखती है, इसलिए इतिहास में कहीं भी बदलाव करने से कड़ी टूट जाती है और यहाँ दिख जाती है।")}</p>
      <div className={`chain ${d.chain.ok ? "ok" : "bad"}`}>
        {d.chain.ok ? (hi ? `✔ कड़ी सुरक्षित — ${d.chain.entries} प्रविष्टियाँ` : `✔ Chain intact — ${d.chain.entries} entr${d.chain.entries === 1 ? "y" : "ies"}`)
                    : (hi ? `✖ प्रविष्टि #${d.chain.broken_at} पर कड़ी टूटी` : `✖ Chain broken at entry #${d.chain.broken_at}`)}
        {d.chain.head && <code> {t("head", "सिरा")} {d.chain.head}</code>}
        <button className="btn sm ghost" onClick={load}>{t("Refresh", "ताज़ा करें")}</button>
      </div>
      {d.entries.length === 0 ? <p className="muted">{t("No trades booked yet.", "अभी कोई सौदा दर्ज नहीं हुआ।")}</p> : (
        <div className="tablewrap"><table className="tbl">
          <thead><tr><th>#</th><th>{t("When", "कब")}</th><th>{t("Trade", "सौदा")}</th><th>{t("Price", "भाव")}</th><th>{t("NAV after", "बाद की क़ीमत")}</th><th>{t("Why", "क्यों")}</th><th>{t("Fingerprint", "फ़िंगरप्रिंट")}</th></tr></thead>
          <tbody>{d.entries.map((e: any) => (
            <tr key={e.id}>
              <td>{e.id}</td><td className="small">{String(e.ts).replace("T", " ").slice(0, 19)}</td>
              <td><b className={e.side === "SELL" ? "neg" : "pos"}>{hi ? (e.side === "SELL" ? "बेचें" : "ख़रीदें") : e.side}</b> {e.shares} {e.ticker?.replace(".NS", "")}</td>
              <td>₹{Number(e.price).toLocaleString("en-IN")}</td><td>{inr(e.nav_after)}</td>
              <td className="small">{hi ? LEDGER_REASON_HI[e.reason] ?? dt(e.reason) : e.reason}</td><td><code>{String(e.hash).slice(0, 10)}</code></td>
            </tr>))}</tbody>
        </table></div>
      )}
    </section>
  );
}

export default function Govern() {
  const { t } = useT();
  const [key, setKey] = useState(0);
  const [tab, setTab] = useState<"check" | "rebalance" | "record" | "tamper">("check");
  const bump = () => setKey((k) => k + 1);
  const TABS: [typeof tab, string, string][] = [
    ["check", "Check a trade", "सौदा जाँचें"], ["rebalance", "Rebalance", "रीबैलेंस"], ["record", "Audit record", "ऑडिट रिकॉर्ड"], ["tamper", "Tamper test", "छेड़छाड़ परीक्षा"],
  ];
  const HELP: Record<typeof tab, [string, string]> = {
    check: ["Type a trade and see it judged against your limits, with the largest size that would fit.", "कोई सौदा लिखिए और देखिए कि वह आपकी सीमाओं पर कैसा उतरता है, और सबसे बड़ा कितना आ सकता है।"],
    rebalance: ["See a fix side by side, before and after, with what it would cost in tax and trading.", "सुधार को साथ-साथ देखिए, पहले और बाद में, टैक्स और ट्रेडिंग की लागत के साथ।"],
    record: ["Every decision, in order, each sealed to the one before it.", "हर फ़ैसला, क्रम से, हर एक पिछले से जुड़ा हुआ।"],
    tamper: ["Edit an old entry on purpose and watch the record catch it.", "जानबूझकर कोई पुरानी प्रविष्टि बदलिए और देखिए रिकॉर्ड उसे पकड़ लेता है।"],
  };
  return (
    <Page title="Govern" lead={t("Rules that no AI can override: check a trade, simulate a fix, and keep an honest record.", "ऐसे नियम जिन्हें कोई AI नहीं बदल सकता: सौदा जाँचिए, सुधार आज़माइए, और ईमानदार रिकॉर्ड रखिए।")}>
      <GovernHero />
      <div className="seg" role="tablist" aria-label={t("Governance tools", "नियम के औज़ार")}>
        {TABS.map(([id, en, hi]) => <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{t(en, hi)}</button>)}
      </div>
      <p className="seg-help">{t(HELP[tab][0], HELP[tab][1])}</p>
      <div className="grid g2" hidden={tab !== "check" && tab !== "rebalance"}>
        {tab === "check" && <Firewall onStage={bump} />}
        {tab === "check" && <RebalanceSim refreshKey={key} onBooked={bump} />}
        {tab === "rebalance" && <RebalanceSim refreshKey={key} onBooked={bump} />}
      </div>
      {tab === "record" && <div className="grid"><Ledger refreshKey={key} /></div>}
      {tab === "tamper" && <div className="grid"><TamperDemo /></div>}
    </Page>
  );
}

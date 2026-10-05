import { useStore } from "../../lib/store";
import { useT } from "../../lib/i18n";

/** The three rules the firewall enforces, drawn as the one thing each of them is: a bar with a line you must not cross
 *  (or, for cash, must not fall under). Always visible at the top of Govern, so every trade you check is judged against
 *  something you can see. */
function Meter({ label, value, limit, floor = false, note }: { label: string; value: number; limit: number; floor?: boolean; note: string }) {
  const { t } = useT();
  const max = Math.max(limit * 1.6, value * 1.15, 0.05);
  const breach = floor ? value < limit : value > limit;
  const room = floor ? value - limit : limit - value;
  return (
    <div className={`gm ${breach ? "breach" : "ok"}`}>
      <div className="gm-top"><span className="gm-label">{label}</span><span className="gm-val">{(value * 100).toFixed(1)}%</span></div>
      <div className="gm-track" role="meter" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={Math.round(max * 100)} aria-label={label}>
        <div className="gm-fill" style={{ width: `${(value / max) * 100}%` }} />
        <div className="gm-limit" style={{ left: `${(limit / max) * 100}%` }}><span>{(limit * 100).toFixed(0)}%</span></div>
      </div>
      <div className="gm-note">{breach
        ? (floor ? t(`${Math.abs(room * 100).toFixed(1)} points short of the minimum. ${note}`, `न्यूनतम से ${Math.abs(room * 100).toFixed(1)} अंक कम। ${note}`) : t(`${Math.abs(room * 100).toFixed(1)} points over your limit. ${note}`, `आपकी सीमा से ${Math.abs(room * 100).toFixed(1)} अंक ऊपर। ${note}`))
        : t(`${(room * 100).toFixed(1)} points of room. ${note}`, `${(room * 100).toFixed(1)} अंक की गुंजाइश। ${note}`)}</div>
    </div>
  );
}

export function GovernHero() {
  const fund = useStore((s) => s.fund);
  const { t } = useT();
  if (!fund?.positions?.length) return null;
  const lim = fund.policy.limits;
  const top = [...fund.positions].sort((a, b) => b.weight - a.weight)[0];
  const sectors = Object.entries(fund.exposures).sort((a, b) => b[1] - a[1]);
  const secName = fund.positions.find((p) => p.sector === sectors[0]?.[0])?.sector_label ?? sectors[0]?.[0];
  const blocked = fund.counters?.violations_blocked ?? 0;
  return (
    <section className="card gov-hero">
      <header>
        <h2>{t("Your limits, right now", "आपकी सीमाएँ, अभी")}</h2>
        <p className="muted">{t(`These are the lines the firewall holds for the "${fund.policy.name ?? fund.policy.profile ?? "current"}" profile. No analyst, model or button can move them without leaving a record.`, `ये वे रेखाएँ हैं जो फ़ायरवॉल "${fund.policy.name ?? fund.policy.profile ?? "मौजूदा"}" प्रोफ़ाइल के लिए थामे रखता है। कोई विश्लेषक, मॉडल या बटन इन्हें बिना रिकॉर्ड छोड़े नहीं हिला सकता।`)}</p>
      </header>
      <div className="gov-meters">
        <Meter label={t("Largest single stock", "सबसे बड़ा एक शेयर")} value={top.weight} limit={lim.max_position_pct ?? 0.05} note={top.name ?? top.ticker} />
        <Meter label={t("Largest industry", "सबसे बड़ा उद्योग")} value={sectors[0]?.[1] ?? 0} limit={lim.max_sector_pct ?? 0.3} note={secName ?? ""} />
        <Meter label={t("Cash kept", "रखा गया नक़द")} value={fund.cash_pct} limit={lim.min_cash_pct ?? 0.1} floor note={t("The floor you set.", "आपकी तय की हुई न्यूनतम सीमा।")} />
      </div>
      <p className="gov-foot">{t(`${blocked} trade${blocked === 1 ? "" : "s"} blocked so far this session. Every decision, approved or not, is written to a record that cannot be quietly edited.`, `इस सत्र में अब तक ${blocked} सौदे रोके गए। हर फ़ैसला, मंज़ूर हो या नहीं, ऐसे रिकॉर्ड में लिखा जाता है जिसे चुपचाप बदला नहीं जा सकता।`)}</p>
    </section>
  );
}

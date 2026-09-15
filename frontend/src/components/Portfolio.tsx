import { useEffect, useMemo, useState } from "react";

import { Panel } from "./Panels";
import { useStore } from "../lib/store";

/* Money in Indian conventions. "₹12,00,000" is how the audience reads it;
   "₹1,200,000" is how a US library formats it, and the difference is jarring. */
export function rupees(n: number): string {
  const a = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`;
  return `${sign}₹${a.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
export const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

interface CatalogueRow {
  ticker: string; name: string; sector: string; sector_label: string; price: number | null;
}

/** Build or load a portfolio. The single change that makes this a tool rather than
 *  a demo: until now there was exactly one hardcoded fund and no way in. */
export function PortfolioBuilder({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<"presets" | "build" | "paste">("presets");
  const [catalogue, setCatalogue] = useState<CatalogueRow[]>([]);
  const [saved, setSaved] = useState<any[]>([]);
  const [presets, setPresets] = useState<any[]>([]);
  const [rows, setRows] = useState<{ ticker: string; shares: number }[]>([]);
  const [search, setSearch] = useState("");
  const [cash, setCash] = useState(50000);
  const [name, setName] = useState("My portfolio");
  const [paste, setPaste] = useState("");
  const [rejected, setRejected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/universe").then((r) => r.json()).then((d) => setCatalogue(d.tickers ?? []));
    refresh();
  }, []);

  const refresh = () =>
    fetch("/portfolios").then((r) => r.json()).then((d) => {
      setSaved(d.portfolios ?? []);
      setPresets(d.presets ?? []);
    });

  const priceOf = useMemo(
    () => Object.fromEntries(catalogue.map((c) => [c.ticker, c.price ?? 0])),
    [catalogue],
  );
  const total = rows.reduce((s, r) => s + (priceOf[r.ticker] ?? 0) * r.shares, 0) + cash;

  const matches = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];
    return catalogue
      .filter((c) => c.name.toLowerCase().includes(q) || c.ticker.toLowerCase().includes(q))
      .slice(0, 8);
  }, [search, catalogue]);

  const add = (ticker: string) => {
    setRows((r) => (r.some((x) => x.ticker === ticker) ? r : [...r, { ticker, shares: 10 }]));
    setSearch("");
  };

  const activate = async (id: string) => {
    setBusy(true);
    await fetch(`/portfolios/${id}/activate`, { method: "POST" });
    setBusy(false);
    onClose();
  };

  const saveNew = async () => {
    setBusy(true);
    await fetch("/portfolios", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, cash,
        positions: Object.fromEntries(rows.filter((r) => r.shares > 0)
          .map((r) => [r.ticker, r.shares])),
      }),
    });
    setBusy(false);
    onClose();
  };

  const doParse = async () => {
    const res = await fetch("/portfolios/parse", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: paste }),
    });
    const d = await res.json();
    setRows((d.positions ?? []).map((p: any) => ({ ticker: p.ticker, shares: p.shares })));
    setRejected(d.rejected ?? []);
    if ((d.positions ?? []).length) setTab("build");
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>Your portfolio</span>
          <button className="btn" onClick={onClose}>Close</button>
        </div>

        <div className="tabs">
          {(["presets", "build", "paste"] as const).map((t) => (
            <div key={t} className={`tab ${tab === t ? "on" : ""}`} onClick={() => setTab(t)}>
              {t === "presets" ? "Start from an example"
                : t === "build" ? "Pick stocks" : "Paste holdings"}
            </div>
          ))}
        </div>

        {tab === "presets" && (
          <div className="modal-body">
            <div className="hint">
              No idea where to start? Load one of these. The first is what most real
              portfolios look like.
            </div>
            {saved.map((p) => {
              const blurb = presets.find((x) => `preset_${x.key}` === p.id)?.blurb;
              return (
                <div className="preset" key={p.id}>
                  <div className="preset-main">
                    <div className="preset-name">
                      {p.name}
                      {!p.is_preset && <span className="badge">saved</span>}
                    </div>
                    <div className="preset-blurb">
                      {blurb ?? `${p.holdings} holdings · ${rupees(p.cash)} cash`}
                    </div>
                  </div>
                  <button className="btn go" disabled={busy}
                          onClick={() => activate(p.id)}>Load</button>
                  {!p.is_preset && (
                    <button className="btn" title="Delete"
                            onClick={async () => {
                              await fetch(`/portfolios/${p.id}`, { method: "DELETE" });
                              refresh();
                            }}>✕</button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "build" && (
          <div className="modal-body">
            <div className="field-row">
              <input className="field" placeholder="Portfolio name" value={name}
                     onChange={(e) => setName(e.target.value)} />
              <input className="field num-field" type="number" value={cash}
                     onChange={(e) => setCash(Number(e.target.value))} />
              <span className="unit">cash ₹</span>
            </div>

            <div className="search-wrap">
              <input className="field" placeholder="Search a company — try 'HDFC' or 'Infosys'"
                     value={search} onChange={(e) => setSearch(e.target.value)} />
              {!!matches.length && (
                <div className="suggest">
                  {matches.map((m) => (
                    <div className="suggest-row" key={m.ticker} onClick={() => add(m.ticker)}>
                      <span>{m.name}</span>
                      <span className="tiny">{m.sector_label}</span>
                      <span className="num">{m.price ? `₹${m.price.toFixed(0)}` : "—"}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {!rows.length && <div className="empty">Search above to add what you own.</div>}
            {rows.map((r, i) => (
              <div className="holding-row" key={r.ticker}>
                <span className="hname">
                  {catalogue.find((c) => c.ticker === r.ticker)?.name ?? r.ticker}
                </span>
                <input className="field qty" type="number" value={r.shares}
                       onChange={(e) => setRows((rs) => rs.map((x, j) =>
                         j === i ? { ...x, shares: Number(e.target.value) } : x))} />
                <span className="num">{rupees((priceOf[r.ticker] ?? 0) * r.shares)}</span>
                <button className="btn"
                        onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}

            {!!rows.length && (
              <div className="modal-foot">
                <span>Total {rupees(total)} · {rows.length} holdings</span>
                <button className="btn go" disabled={busy} onClick={saveNew}>
                  Analyse this portfolio
                </button>
              </div>
            )}
          </div>
        )}

        {tab === "paste" && (
          <div className="modal-body">
            <div className="hint">
              Paste straight from your broker. One holding per line — a name or symbol,
              then the quantity. Commas, tabs or spaces all work.
            </div>
            <textarea className="field paste" rows={8} value={paste}
                      placeholder={"TCS, 40\nHDFC Bank, 120\nInfosys 85\nRELIANCE,30"}
                      onChange={(e) => setPaste(e.target.value)} />
            <div className="modal-foot">
              <span className="tiny">Anything I cannot read is shown back, not dropped.</span>
              <button className="btn go" onClick={doParse}>Read it</button>
            </div>
            {!!rejected.length && (
              <div className="reject-list">
                <b>Could not read {rejected.length} line(s):</b>
                {rejected.slice(0, 5).map((r, i) => <div key={i}>{r}</div>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Which limits am I being judged against? Never let a score appear without it. */
export function ProfileSwitch() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [active, setActive] = useState<string>("");
  const fund = useStore((s) => s.fund);

  useEffect(() => {
    fetch("/profiles").then((r) => r.json()).then((d) => {
      setProfiles(d.profiles ?? []);
      setActive(d.active ?? "");
    });
  }, [fund?.policy?.profile]);

  const pick = async (key: string) => {
    setActive(key);
    await fetch(`/profiles/${key}`, { method: "POST" });
  };

  if (!profiles.length) return null;
  const current = profiles.find((p) => p.key === active);
  return (
    <Panel title="Who are you?">
      <div className="seg">
        {profiles.map((p) => (
          <div key={p.key} className={`seg-item ${active === p.key ? "on" : ""}`}
               onClick={() => pick(p.key)}>{p.name.split(" ")[0]}</div>
        ))}
      </div>
      {current && <div className="hint" style={{ marginTop: 7 }}>{current.blurb}</div>}
      {current && (
        <div className="tiny" style={{ marginTop: 6 }}>
          Max {pct(current.limits.max_position_pct)} per stock ·{" "}
          {pct(current.limits.max_sector_pct)} per industry ·{" "}
          {pct(current.limits.min_cash_pct)} cash
        </div>
      )}
    </Panel>
  );
}

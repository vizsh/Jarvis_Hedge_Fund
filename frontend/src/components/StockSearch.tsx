import { useEffect, useRef, useState } from "react";

import "../styles-search.css";
import { useT } from "../lib/i18n";
import { send } from "../lib/socket";
import { useStore } from "../lib/store";

interface Hit { symbol: string; name: string; exchange: string; covered: boolean }

/** Type any listed company, pick it from the suggestions, and run the research desks on it.
 *  A company the snapshot has no data for is fetched first (prices, filings, headlines). */
export function StockSearch() {
  const { t } = useT();
  const orb = useStore((s) => s.orb);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [picked, setPicked] = useState<Hit | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const seq = useRef(0);

  useEffect(() => {
    if (picked && q === picked.name) return;               // the box just filled itself from a pick
    const text = q.trim();
    if (!text) { setHits([]); return; }
    const id = ++seq.current;
    const timer = window.setTimeout(() => {
      fetch(`/stocks/search?q=${encodeURIComponent(text)}&limit=8`).then((r) => r.json()).then((d) => {
        if (id !== seq.current) return;                    // an older answer must not overwrite a newer one
        setHits(d.results ?? []); setActive(0); setOpen(true);
      }).catch(() => {});
    }, 140);
    return () => window.clearTimeout(timer);
  }, [q]); // eslint-disable-line

  useEffect(() => {
    const away = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, []);

  const choose = (h: Hit) => { setPicked(h); setQ(h.name); setOpen(false); setStatus(""); };

  const run = async (h: Hit | null = picked ?? hits[0] ?? null) => {
    if (!h || busy) return;
    setPicked(h); setQ(h.name); setOpen(false); setBusy(true);
    try {
      if (!h.covered) {
        setStatus(t(`Fetching prices, filings and news for ${h.name}…`, `${h.name} के भाव, फ़ाइलिंग और ख़बरें ला रहा हूँ…`));
        const r = await fetch("/stocks/add", { method: "POST", headers: { "Content-Type": "application/json" },
                                              body: JSON.stringify({ symbol: h.symbol, name: h.name }) }).then((x) => x.json());
        if (!r.ok) { setStatus(r.message ?? t("No price history found for that company.", "उस कंपनी का भाव-इतिहास नहीं मिला।")); return; }
        setHits((l) => l.map((x) => (x.symbol === h.symbol ? { ...x, covered: true } : x)));
      }
      setStatus("");
      send(`analyse ${h.symbol}`, t(`analyse ${h.name}`, `${h.name} का विश्लेषण`));
    } catch {
      setStatus(t("Could not fetch that company. Check the connection and try again.", "उस कंपनी का डेटा नहीं ला सका। कनेक्शन जाँचकर फिर कोशिश कीजिए।"));
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setActive((a) => Math.min(a + 1, hits.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Escape") setOpen(false);
    else if (e.key === "Enter") { e.preventDefault(); void run(open && hits[active] ? hits[active] : picked ?? hits[0] ?? null); }
  };

  return (
    <div className="stocksearch" ref={box}>
      <div className="row">
        <div className="ss-field">
          <input id="research-ticker" value={q} role="combobox" aria-expanded={open} aria-controls="ss-list" aria-autocomplete="list"
                 placeholder={t("Search any listed company, e.g. Zomato, Tata Motors, IRCTC", "कोई भी सूचीबद्ध कंपनी खोजिए, जैसे Zomato, Tata Motors, IRCTC")}
                 onChange={(e) => { setQ(e.target.value); setPicked(null); setStatus(""); }}
                 onFocus={() => hits.length && setOpen(true)} onKeyDown={onKey} autoComplete="off" />
          {open && hits.length > 0 && (
            <ul id="ss-list" className="ss-list" role="listbox">
              {hits.map((h, i) => (
                <li key={h.symbol} role="option" aria-selected={i === active} className={i === active ? "on" : ""}
                    onMouseEnter={() => setActive(i)} onMouseDown={(e) => { e.preventDefault(); choose(h); }}>
                  <span className="ss-sym">{h.symbol.replace(".NS", "")}</span>
                  <span className="ss-name">{h.name}</span>
                  <span className="ss-ex">{h.exchange}</span>
                  <span className={`ss-tag ${h.covered ? "ready" : "fetch"}`}>{h.covered ? t("data ready", "डेटा तैयार") : t("will fetch", "लाया जाएगा")}</span>
                </li>))}
            </ul>)}
        </div>
        <button className="btn go" disabled={busy || orb === "thinking" || (!picked && !hits.length)} onClick={() => void run()}>
          {orb === "thinking" ? t("Analysing… (about 30 seconds)", "विश्लेषण हो रहा है… (लगभग 30 सेकंड)") : busy ? t("Fetching…", "ला रहा हूँ…") : t("Run the analysts", "विश्लेषक चलाइए")}
        </button>
      </div>
      {status && <div className="ss-status" role="status">{status}</div>}
    </div>
  );
}

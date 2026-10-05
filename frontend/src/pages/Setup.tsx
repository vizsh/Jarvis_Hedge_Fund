import { useEffect, useMemo, useState } from "react";

import "../styles-setup.css";
import { useLang } from "../lib/lang";
import { go } from "../lib/router";
import { type Persona, useSetup } from "../lib/setup";
import { Icon } from "../components/Icon";
import { Page } from "./Page";

const money = (n: number, hi: boolean) => (n === 0 ? (hi ? "मुफ़्त" : "Free") : `₹${n}${hi ? " / माह" : " / month"}`);

/** First-run setup: pick a starting basket, then add or remove features. Nothing is charged; prices are for the pitch. */
export function Setup() {
  const hi = useLang((s) => s.lang) === "hi";
  const { all, personas, features, done, save } = useSetup();
  const [pick, setPick] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string[]>(features.filter((f) => f !== "home"));
  const [saved, setSaved] = useState(false);
  useEffect(() => { if (done) setChosen(features.filter((f) => f !== "home")); }, [done]);

  const paid = useMemo(() => all.filter((f) => f.tier === "paid" && chosen.includes(f.id)), [all, chosen]);
  const total = paid.reduce((s, f) => s + f.price, 0);
  const pickBasket = (p: Persona) => { setPick(p.id); setChosen([...p.features]); };
  const toggle = (id: string) => setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id]));
  const start = async () => {
    await save(pick, chosen);
    setSaved(true);
    setTimeout(() => go("/"), 350);
  };
  const name = (id: string) => { const f = all.find((x) => x.id === id); return f ? (hi ? f.hi : f.en) : id; };

  return (
    <Page title={hi ? "अपना प्रोटोटाइप सेट कीजिए" : "Set up your prototype"}
          lead={hi ? "पहले एक शुरुआती सेट चुनिए, फिर जो चाहें जोड़ें या हटाएँ। कोई पैसा नहीं लिया जाता; क़ीमतें सिर्फ़ दिखाने के लिए हैं।"
                   : "Start from a basket that fits who you are, then add or remove features. Nothing is charged; prices are shown for the pitch."}>
      <h2 className="su-h">{hi ? "1. शुरुआती सेट चुनिए" : "1. Pick a starting basket"}</h2>
      <div className="su-baskets">
        {personas.map((p) => (
          <button key={p.id} className={`su-basket ${pick === p.id ? "on" : ""}`} onClick={() => pickBasket(p)} aria-pressed={pick === p.id}>
            <span className="su-bname">{hi ? p.hi : p.en}</span>
            <span className="su-who">{hi ? p.who_hi : p.who}</span>
            <span className="su-chips">{p.features.filter((f) => f !== "home").map((f) => <i key={f}>{name(f)}</i>)}</span>
            <span className="su-price">{money(p.price, hi)}</span>
          </button>))}
      </div>

      <h2 className="su-h">{hi ? "2. अपनी सूची बनाइए" : "2. Build your list"}</h2>
      <div className="su-list">
        {all.filter((f) => f.id !== "home").map((f) => (
          <label key={f.id} className={`su-feat ${chosen.includes(f.id) ? "on" : ""}`}>
            <input type="checkbox" checked={chosen.includes(f.id)} onChange={() => toggle(f.id)} />
            <span className="su-fname">{hi ? f.hi : f.en}</span>
            <span className={`su-tier ${f.tier}`}>{money(f.price, hi)}</span>
            <span className="su-fblurb">{hi ? f.blurb_hi : f.blurb}</span>
          </label>))}
      </div>

      <div className="su-foot">
        <div>
          <b>{hi ? "इस सेटअप की क़ीमत (डेमो)" : "This setup (demo price)"}:</b> {total === 0 ? (hi ? "मुफ़्त" : "Free") : `₹${total} ${hi ? "/ माह" : "/ month"}`}
          <small>{hi ? "असली भुगतान नहीं होता। यह पिच के लिए दिखाया गया अनुमान है।" : "No payment is taken. This is an estimate shown for the pitch."}</small>
        </div>
        <button className="btn go" onClick={start} disabled={chosen.length === 0 || saved}>
          <Icon name="arrow" size={16} /> {saved ? (hi ? "शुरू हो रहा है…" : "Starting…") : (hi ? "शुरू कीजिए" : "Start with these")}
        </button>
      </div>
    </Page>
  );
}

/** A feature that is not in this prototype yet: say what it does and add it in one tap. */
export function Locked({ route }: { route: string }) {
  const hi = useLang((s) => s.lang) === "hi";
  const { all, features, save } = useSetup();
  const f = all.find((x) => route.replace(/^\//, "").split("?")[0] === x.id);
  if (!f) return null;
  const add = async () => { await save(null, [...features.filter((x) => x !== "home"), f.id]); go(f.route); };
  return (
    <Page title={hi ? f.hi : f.en} lead={hi ? f.blurb_hi : f.blurb}>
      <section className="card su-locked">
        <p>{hi ? "यह फ़ीचर आपके प्रोटोटाइप में अभी नहीं है। जोड़ने के बाद यह पूरी तरह काम करेगा।" : "This feature is not in your prototype yet. Once added, it works in full."}</p>
        <button className="btn go" onClick={add}>{hi ? "मेरे प्रोटोटाइप में जोड़िए" : "Add to my prototype"} · {money(f.price, hi)}</button>
        <button className="btn ghost" onClick={() => go("/setup")}>{hi ? "पूरी सूची बदलिए" : "Change my setup"}</button>
      </section>
    </Page>
  );
}

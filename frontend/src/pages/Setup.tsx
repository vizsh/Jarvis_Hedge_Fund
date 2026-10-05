import { useEffect, useMemo, useRef, useState } from "react";

import "../styles-setup.css";
import { useLang } from "../lib/lang";
import { go } from "../lib/router";
import { type Feat, type Persona, useSetup } from "../lib/setup";
import { Page } from "./Page";

const rupee = (n: number) => `₹${n.toLocaleString("en-IN")}`;

/** Counts from the old value to the new one, so a price change reads as a change rather than a jump. */
function useCount(target: number) {
  const [v, setV] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const a = from.current, d = 380;
    let start = -1, raf = 0;
    const tick = (now: number) => {
      if (start < 0) start = now;
      const k = Math.max(0, Math.min(1, (now - start) / d)), e = 1 - Math.pow(1 - k, 3);
      setV(Math.round(a + (target - a) * e));
      if (k < 1) raf = requestAnimationFrame(tick); else from.current = target;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return v;
}

/** Setup: choose who this prototype is for, then switch features on and off. A live panel shows the menu and the demo price. */
export function Setup() {
  const hi = useLang((s) => s.lang) === "hi";
  const { all, personas, features, done, save } = useSetup();
  const [basket, setBasket] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string[]>(features.filter((f) => f !== "home"));
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (done) setChosen(features.filter((f) => f !== "home")); }, [done]);

  const feats = all.filter((f) => f.id !== "home");
  const paid = feats.filter((f) => f.tier === "paid" && chosen.includes(f.id));
  const total = paid.reduce((s, f) => s + f.price, 0);
  const shown = useCount(total);
  const menu = [all.find((f) => f.id === "home"), ...feats.filter((f) => chosen.includes(f.id))].filter(Boolean) as Feat[];
  const persona = personas.find((p) => p.id === basket);

  const pick = (p: Persona) => { setBasket(p.id); setChosen([...p.features]); };
  const toggle = (id: string) => { setBasket(null); setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : [...c, id])); };
  const start = async () => {
    setBusy(true);
    await save(basket, chosen);
    go("/");
  };
  const name = (f: Feat) => (hi ? f.hi : f.en);

  return (
    <Page title={hi ? "प्रोटोटाइप सेट कीजिए" : "Set up your prototype"}
          lead={hi ? "पहले बताइए यह किसके लिए है, फिर सुविधाएँ चालू या बंद कीजिए। कोई भुगतान नहीं होता।" : "Say who this is for, then switch features on or off. Nothing is charged."}>
      <div className="su">
        <div className="su-main">
          <section className="su-sec">
            <header><span className="su-n">1</span><h2>{hi ? "यह किसके लिए है?" : "Who is it for?"}</h2></header>
            <div className="su-pick" role="radiogroup" aria-label={hi ? "शुरुआती सेट" : "Starting basket"}>
              {personas.map((p) => (
                <button key={p.id} role="radio" aria-checked={basket === p.id} className={`su-opt ${basket === p.id ? "on" : ""}`} onClick={() => pick(p)}>
                  <span className="su-dot" aria-hidden />
                  <span className="su-otext">
                    <b>{hi ? p.hi : p.en}</b>
                    <small>{hi ? p.who_hi : p.who}</small>
                  </span>
                  <span className="su-oprice">{p.price === 0 ? (hi ? "मुफ़्त" : "Free") : `${rupee(p.price)}/${hi ? "माह" : "mo"}`}</span>
                </button>))}
            </div>
          </section>

          <section className="su-sec">
            <header><span className="su-n">2</span><h2>{hi ? "सुविधाएँ चुनिए" : "Choose features"}</h2>
              <small>{chosen.length} {hi ? "चालू" : "on"}{persona && <> · {hi ? "शुरुआत" : "from"} <i>{hi ? persona.hi : persona.en}</i></>}</small></header>
            {(["free", "paid"] as const).map((tier) => (
              <div className="su-group" key={tier}>
                <h3>{tier === "free" ? (hi ? "हमेशा मुफ़्त" : "Always free") : (hi ? "सशुल्क" : "Paid")}</h3>
                <ul className="su-rows">
                  {feats.filter((f) => f.tier === tier).map((f) => {
                    const on = chosen.includes(f.id);
                    return (
                      <li key={f.id}>
                        <button className={`su-row ${on ? "on" : ""}`} role="switch" aria-checked={on} onClick={() => toggle(f.id)}>
                          <span className="su-rtext">
                            <b>{name(f)}</b>
                            <small>{hi ? f.blurb_hi : f.blurb}</small>
                          </span>
                          <span className="su-rprice">{f.price ? `${rupee(f.price)}` : (hi ? "मुफ़्त" : "Free")}</span>
                          <span className="su-switch" aria-hidden><i /></span>
                        </button>
                      </li>);
                  })}
                </ul>
              </div>))}
          </section>
        </div>

        <aside className="su-side" aria-label={hi ? "सारांश" : "Summary"}>
          <div className="su-live">
            <h3>{hi ? "आपका मेनू" : "Your menu"}</h3>
            <div className="su-menu" aria-live="polite">
              {menu.map((f) => <span key={f.id} className={f.id === "home" ? "home" : ""}>{name(f)}</span>)}
            </div>
            <div className="su-total">
              <span>{hi ? "डेमो मासिक क़ीमत" : "Demo monthly price"}</span>
              <b>{shown === 0 ? (hi ? "मुफ़्त" : "Free") : `${rupee(shown)}`}</b>
              <small>{hi ? "भुगतान नहीं लिया जाता। यह केवल पिच का अनुमान है।" : "No payment is taken. An estimate for the pitch."}</small>
            </div>
            <button className="su-start" onClick={start} disabled={chosen.length === 0 || busy}>
              {busy ? (hi ? "शुरू हो रहा है…" : "Starting…") : (hi ? "इसी से शुरू कीजिए" : "Start with this")}
            </button>
            <p className="su-hint">{hi ? "बाद में किसी भी समय यहीं से बदल सकते हैं।" : "You can change this any time from My setup."}</p>
          </div>
        </aside>
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
      <section className="su-locked">
        <p>{hi ? "यह सुविधा अभी आपके प्रोटोटाइप में नहीं है। जोड़ते ही यह पूरी तरह काम करेगी।" : "This feature is not in your prototype yet. Add it and it works in full straight away."}</p>
        <div className="su-lrow">
          <button className="su-start" onClick={add}>{hi ? "जोड़िए" : "Add it"} · {f.price ? rupee(f.price) : (hi ? "मुफ़्त" : "Free")}</button>
          <button className="su-ghost" onClick={() => go("/setup")}>{hi ? "पूरी सेटिंग देखिए" : "See my setup"}</button>
        </div>
      </section>
    </Page>
  );
}

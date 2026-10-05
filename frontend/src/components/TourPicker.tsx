import { useEffect, useMemo, useState } from "react";

import { useLang } from "../lib/lang";
import { startTour, type TourEntry } from "../lib/tour";
import { Icon } from "./Icon";

/** Every feature that has a guided tour. Press one and the page opens it and walks you through it, reading each part aloud. */
export function TourPicker() {
  const lang = useLang((s) => s.lang);
  const hi = lang === "hi";
  const [tours, setTours] = useState<TourEntry[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => { fetch(`/tours?lang=${lang}`).then((r) => r.json()).then((d) => setTours(d.tours ?? [])).catch(() => {}); }, [lang]);
  const shown = useMemo(() => {
    const k = q.trim().toLowerCase();
    return k ? tours.filter((t) => (t.title + " " + t.blurb).toLowerCase().includes(k)) : tours;
  }, [tours, q]);
  if (!tours.length) return null;
  return (
    <section className="as-card as-tours" data-tour="tours" aria-label={hi ? "निर्देशित सैर" : "Guided tours"}>
      <header>
        <h3>{hi ? "हर फ़ीचर की निर्देशित सैर" : "Guided tour of any feature"}</h3>
        <p>{hi ? "एक चुनिए: पेज खुलेगा, हर हिस्सा चमकेगा और मैं उसे बोलकर समझाऊँगा।" : "Pick one: the page opens, each part lights up and I explain it aloud."}</p>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={hi ? "फ़ीचर खोजिए…" : "Find a feature…"} aria-label={hi ? "फ़ीचर खोजिए" : "Find a feature"} />
      </header>
      <ul>
        {shown.map((t) => (
          <li key={t.id}>
            <button onClick={() => startTour(t.id)}>
              <span className="tp-ic"><Icon name="arrow" size={14} /></span>
              <span className="tp-t"><b>{t.title}</b><small>{t.blurb}</small></span>
              <span className="tp-n">{t.steps} {hi ? "चरण" : "steps"}</span>
            </button>
          </li>))}
        {!shown.length && <li className="tp-none">{hi ? "ऐसा कोई फ़ीचर नहीं मिला।" : "No feature matches that."}</li>}
      </ul>
    </section>
  );
}

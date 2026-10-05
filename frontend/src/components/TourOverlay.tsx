import { useEffect, useLayoutEffect, useRef, useState } from "react";

import "../styles-tour.css";

import { useLang } from "../lib/lang";
import { go } from "../lib/router";
import { narrate, openRoute, useTour } from "../lib/tour";
import { Icon } from "./Icon";

interface Box { x: number; y: number; w: number; h: number }
const PAD = 10;

function find(sel: string | null): HTMLElement | null {
  if (!sel) return null;
  try { return document.querySelector<HTMLElement>(sel); } catch { return null; }
}

const sleep = (ms: number) => new Promise((r) => window.setTimeout(r, ms));

async function waitFor(sel: string | null, ms = 3500): Promise<HTMLElement | null> {
  if (!sel) return null;
  const t0 = performance.now();
  while (performance.now() - t0 < ms) {
    const el = find(sel);
    if (el && el.getBoundingClientRect().width > 0) return el;
    await sleep(90);
  }
  return null;
}

/** The walk-through player: opens the page, presses what the step presses, spotlights the part being explained and
 *  reads its caption aloud. Back, Next, Pause and Stop are always there; Esc and the arrow keys work too. */
export function TourOverlay() {
  const { tour, i, auto, done, loading, next, prev, stop, goTo, setAuto, start } = useTour();
  const hi = useLang((s) => s.lang) === "hi";
  const lang = useLang((s) => s.lang);
  const step = tour?.steps[i];
  const [box, setBox] = useState<Box | null>(null);
  const [ghost, setGhost] = useState<{ x: number; y: number; tap: boolean } | null>(null);
  const [placed, setPlaced] = useState(false);
  const target = useRef<HTMLElement | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const [cardPos, setCardPos] = useState<{ left: number; top: number } | null>(null);
  const autoRef = useRef(auto);
  autoRef.current = auto;

  // Run the step: open its page, press its button, find its part, read its caption.
  useEffect(() => {
    if (!tour || !step || done) return;
    let alive = true;
    let stopNarration: (() => void) | null = null;
    setPlaced(false);
    setBox(null);
    setGhost(null);
    target.current = null;
    (async () => {
      openRoute(step.route);
      await sleep(260);
      if (step.click) {
        const btn = await waitFor(step.click);
        if (!alive) return;
        if (btn) {
          btn.scrollIntoView({ block: "center", behavior: "smooth" });
          await sleep(350);
          const r = btn.getBoundingClientRect();
          setGhost({ x: r.left + r.width / 2, y: r.top + r.height / 2, tap: false });
          await sleep(650);
          if (!alive) return;
          setGhost({ x: r.left + r.width / 2, y: r.top + r.height / 2, tap: true });
          await sleep(220);
          btn.click();
          await sleep(480);
          if (!alive) return;
          setGhost(null);
        }
      }
      const el = (await waitFor(step.sel, step.click ? 2500 : 3500)) ?? null;
      if (!alive) return;
      target.current = el;
      if (el) {
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        await sleep(420);
      }
      if (!alive) return;
      setPlaced(true);
      const line = `${step.title}. ${step.body}`;
      stopNarration = narrate(line, lang, () => { if (alive && autoRef.current) next(); });
    })();
    return () => { alive = false; stopNarration?.(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tour, i, done, lang]);

  // Follow the part as the page scrolls, resizes or re-flows.
  useEffect(() => {
    if (!tour || done) return;
    let raf = 0;
    let last = "";
    const loop = () => {
      const el = target.current;
      let b: Box | null = null;
      if (el && el.isConnected) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) b = { x: r.left - PAD, y: r.top - PAD, w: r.width + PAD * 2, h: r.height + PAD * 2 };
      }
      const k = b ? `${Math.round(b.x)},${Math.round(b.y)},${Math.round(b.w)},${Math.round(b.h)}` : "";
      if (k !== last) { last = k; setBox(b); }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [tour, done, i]);

  // Keep the caption beside the highlighted part, inside the screen.
  useLayoutEffect(() => {
    const c = card.current;
    if (!c || !tour) return;
    const vw = window.innerWidth, vh = window.innerHeight;
    const cw = c.offsetWidth, ch = c.offsetHeight;
    const m = 14;
    if (!box || box.h > vh * 0.62) { setCardPos({ left: Math.max(m, (vw - cw) / 2), top: vh - ch - 22 }); return; }
    const below = vh - (box.y + box.h) - m, above = box.y - m;
    let top: number;
    if (below >= ch) top = box.y + box.h + m;
    else if (above >= ch) top = box.y - ch - m;
    else top = Math.max(m, vh - ch - 22);
    const left = Math.min(Math.max(m, box.x + box.w / 2 - cw / 2), vw - cw - m);
    setCardPos({ left, top });
  }, [box, i, tour, done, hi]);

  useEffect(() => {
    if (!tour) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") stop();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [tour, next, prev, stop]);

  if (loading && !tour) return <div className="tour-loading" role="status">{hi ? "सैर तैयार हो रही है…" : "Getting the tour ready…"}</div>;
  if (!tour || !step) return null;
  const n = tour.steps.length;

  return (
    <div className="tour" role="dialog" aria-modal="false" aria-label={tour.title}>
      {box && !done ? (
        <div className="tour-spot" style={{ left: box.x, top: box.y, width: box.w, height: box.h }} />
      ) : (
        <div className="tour-dim" />
      )}
      {ghost && (
        <div className={`tour-ghost ${ghost.tap ? "tap" : ""}`} style={{ left: ghost.x, top: ghost.y }} aria-hidden>
          <svg width="26" height="26" viewBox="0 0 24 24"><path d="M5 3l14 8-6 2 4 7-3 1.5-4-7-5 4z" fill="var(--strong)" stroke="var(--bg)" strokeWidth="1.2" strokeLinejoin="round" /></svg>
          <i />
        </div>
      )}
      <div ref={card} className={`tour-card ${placed || done ? "in" : ""}`} style={cardPos ? { left: cardPos.left, top: cardPos.top } : { left: 20, top: 90 }}>
        {done ? (
          <>
            <div className="tour-kicker">{tour.title}</div>
            <h3>{hi ? "सैर पूरी हुई" : "That is the whole tour"}</h3>
            <p>{hi ? "आप इसे दोबारा चला सकते हैं, चैट पर लौट सकते हैं, या सीधे इसे आज़मा सकते हैं।" : "Replay it, go back to the chat, or just start using it. Everything you saw is live: nothing was a mock-up."}</p>
            <div className="tour-actions">
              <button className="tour-btn" onClick={() => void start(tour.id)}>{hi ? "दोबारा चलाइए" : "Replay"}</button>
              <button className="tour-btn" onClick={() => { stop(); go("/assistant"); }}>{hi ? "चैट पर लौटिए" : "Back to the chat"}</button>
              <button className="tour-btn primary" onClick={stop}>{hi ? "बंद करें" : "Close"}</button>
            </div>
          </>
        ) : (
          <>
            <div className="tour-top">
              <span className="tour-kicker">{tour.title} · {i + 1} / {n}</span>
              <button className="tour-x" onClick={stop} aria-label={hi ? "सैर बंद करें" : "Stop the tour"} title="Esc"><Icon name="close" size={15} /></button>
            </div>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
            <div className="tour-bar" aria-hidden><i style={{ width: `${((i + 1) / n) * 100}%` }} /></div>
            <div className="tour-actions">
              <button className="tour-btn" onClick={prev} disabled={i === 0}>{hi ? "← पीछे" : "← Back"}</button>
              <button className={`tour-btn ${auto ? "on" : ""}`} onClick={() => setAuto(!auto)} aria-pressed={auto} title={hi ? "अपने-आप आगे बढ़ना" : "Move on by itself when the caption ends"}>
                {auto ? (hi ? "⏸ अपने-आप" : "⏸ Auto") : (hi ? "▶ अपने-आप" : "▶ Auto")}
              </button>
              <button className="tour-btn primary" onClick={() => (i === n - 1 ? goTo(n) : next())}>{i === n - 1 ? (hi ? "पूरा करें" : "Finish") : (hi ? "आगे →" : "Next →")}</button>
            </div>
            <div className="tour-dots" role="tablist">
              {tour.steps.map((s, k) => <button key={k} className={k === i ? "on" : k < i ? "past" : ""} onClick={() => goTo(k)} aria-label={s.title} title={s.title} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

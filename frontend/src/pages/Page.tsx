import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLang } from "../lib/lang";
import { HI_LABEL } from "../lib/router";

/** One consistent frame for every page: a title, one sentence of purpose, then content. */
export function Page({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  const hi = useLang((s) => s.lang) === "hi";
  const ref = useRef<HTMLElement>(null);
  const [heads, setHeads] = useState<{ text: string; el: HTMLElement }[]>([]);
  const [tall, setTall] = useState(false);
  // Long pages (Govern is about 5,000 px) get a row of links to their sections. Read after render so it
  // follows whatever the panels draw, and left out when there are few sections.
  useEffect(() => {
    const find = () => {
      setTall((ref.current?.scrollHeight ?? 0) > 2200);
      const hs = [...(ref.current?.querySelectorAll<HTMLElement>(".card > h2, .panel > h2, section > h2, .panel > .panel-head h2") ?? [])]
        .filter((h) => h.innerText.trim().length > 1 && h.closest(".rural-card") === null);
      setHeads((old) => (old.length === hs.length && old.every((o, i) => o.el === hs[i]) ? old : hs.map((el) => ({ text: el.innerText.trim(), el }))));
    };
    find();
    const id = window.setTimeout(find, 1200);
    const mo = new MutationObserver(() => find());
    if (ref.current) mo.observe(ref.current, { childList: true, subtree: true });
    return () => { window.clearTimeout(id); mo.disconnect(); };
  }, [title]);
  return (
    <main className="page" ref={ref}>
      <div className="page-head">
        <h1>{hi ? HI_LABEL[title] ?? title : title}</h1>
        <p>{lead}</p>
      </div>
      {heads.length >= 3 && tall && (
        <div className="jumpbar" role="navigation" aria-label={hi ? "इस पेज के भाग" : "On this page"}>
          {heads.map((h, i) => <button key={i} onClick={() => h.el.scrollIntoView({ behavior: "smooth", block: "start" })}>{h.text.length > 26 ? h.text.slice(0, 25) + "…" : h.text}</button>)}
        </div>
      )}
      {children}
    </main>
  );
}

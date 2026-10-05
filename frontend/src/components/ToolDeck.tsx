import { useRef, type ReactNode } from "react";

import { Icon } from "./Icon";

export interface Tool { id: string; icon: string; title: string; blurb: string; tone?: "urgent" }

/** A page's tools as a row of selectable cards, with the chosen tool open underneath. The cards are the navigation,
 *  so there is no separate tab bar, and a page shows one tool at a time instead of every tool stacked in one long scroll. */
export function ToolDeck({ tools, active, onPick, children, label }: { tools: Tool[]; active: string; onPick: (id: string) => void; children: ReactNode; label: string }) {
  const stage = useRef<HTMLDivElement>(null);
  const pick = (id: string) => {
    onPick(id);
    window.setTimeout(() => { if (window.innerWidth < 900) stage.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, 30);
  };
  return (
    <>
      <div className="deck" role="tablist" aria-label={label}>
        {tools.map((x) => (
          <button key={x.id} role="tab" aria-selected={active === x.id} className={`deck-card ${active === x.id ? "on" : ""} ${x.tone ?? ""}`} onClick={() => pick(x.id)}>
            <span className="deck-ic"><Icon name={x.icon} size={20} /></span>
            <span className="deck-t">{x.title}</span>
            <span className="deck-b">{x.blurb}</span>
          </button>))}
      </div>
      <div className="deck-stage" ref={stage} role="tabpanel">{children}</div>
    </>
  );
}

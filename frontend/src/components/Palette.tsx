import { useEffect, useRef, useState } from "react";

import { useGuide } from "../lib/guide";
import { send } from "../lib/socket";

interface Row {
  id: string; label: string; hint: string; group: string;
  kind: "question" | "flow" | "panel" | "endpoint" | "action";
  payload: string; shortcut: string | null;
}

/** Ctrl+K: every capability in one searchable list, in the words a person would type.
 *
 *  Discoverability here used to depend on already knowing that the correlation matrix
 *  lives under "Fund desk". Nobody knows that on a first visit. Searching "too much in
 *  one place" and landing on the right thing is the fix. */
export function Palette() {
  const open = useGuide((s) => s.palette);
  const close = useGuide((s) => s.closePalette);
  const openPalette = useGuide((s) => s.openPalette);
  const startFlow = useGuide((s) => s.startFlow);
  const setReport = useGuide((s) => s.setReport);
  const setOnboarding = useGuide((s) => s.setOnboarding);

  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  // Ctrl+K from anywhere, including from inside a text field — that is the one
  // shortcut people expect to always work.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        open ? close() : openPalette();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close, openPalette]);

  useEffect(() => {
    if (!open) { setQ(""); setCursor(0); return; }
    input.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    fetch(`/palette?q=${encodeURIComponent(q)}`)
      .then((r) => r.json())
      .then((d) => { if (!cancelled) { setRows(d.results ?? []); setCursor(0); } })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [q, open]);

  if (!open) return null;

  const run = (row: Row) => {
    close();
    switch (row.kind) {
      case "question":
        send(row.payload);
        break;
      case "flow":
        void startFlow(row.payload);
        break;
      case "endpoint":
        if (row.payload.startsWith("/")) void fetch(row.payload, { method: "POST" });
        else send(row.payload);
        break;
      case "action":
        if (row.payload === "report") setReport(true);
        else if (row.payload === "builder") setOnboarding(true);
        else if (row.payload === "mute") window.dispatchEvent(new CustomEvent("jarvis:mute"));
        else window.dispatchEvent(new CustomEvent("jarvis:open", { detail: row.payload }));
        break;
      case "panel":
        window.dispatchEvent(new CustomEvent("jarvis:open", { detail: row.payload }));
        break;
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { e.preventDefault(); close(); }
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, rows.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
    if (e.key === "Enter" && rows[cursor]) { e.preventDefault(); run(rows[cursor]); }
  };

  return (
    <div className="pal-wrap" onClick={close}>
      <div className="pal" onClick={(e) => e.stopPropagation()}>
        <input ref={input} className="pal-input" value={q} onKeyDown={onKey}
               onChange={(e) => setQ(e.target.value)}
               placeholder="What do you want to do? Type it however you'd say it…" />
        <div className="pal-rows">
          {rows.map((r, i) => (
            <div className={`pal-row ${i === cursor ? "on" : ""}`} key={r.id}
                 onMouseEnter={() => setCursor(i)} onClick={() => run(r)}>
              <span className={`pal-group g-${r.group.replace(/\s/g, "")}`}>{r.group}</span>
              <span className="pal-label">{r.label}</span>
              <span className="pal-hint">{r.hint}</span>
              {r.shortcut && <kbd className="pal-kbd">{r.shortcut}</kbd>}
            </div>
          ))}
          {!rows.length && (
            <div className="pal-empty">
              Nothing matches that. Try “risk”, “sell”, “tax”, or “what if”.
            </div>
          )}
        </div>
        <div className="pal-foot">
          <kbd>↑</kbd><kbd>↓</kbd> move · <kbd>↵</kbd> run · <kbd>esc</kbd> close
        </div>
      </div>
    </div>
  );
}

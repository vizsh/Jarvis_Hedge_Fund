import type { ReactNode } from "react";
import { useLang } from "../lib/lang";
import { HI_LABEL } from "../lib/router";

/** One consistent frame for every page: a title, one sentence of purpose, then content. */
export function Page({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  const hi = useLang((s) => s.lang) === "hi";
  return (
    <main className="page">
      <div className="page-head">
        <h1>{hi ? HI_LABEL[title] ?? title : title}</h1>
        <p>{lead}</p>
      </div>
      {children}
    </main>
  );
}

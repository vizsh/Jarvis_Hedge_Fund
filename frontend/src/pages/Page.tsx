import type { ReactNode } from "react";

/** One consistent frame for every page: a title, one sentence of purpose, then content. */
export function Page({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return (
    <main className="page">
      <div className="page-head">
        <h1>{title}</h1>
        <p>{lead}</p>
      </div>
      {children}
    </main>
  );
}

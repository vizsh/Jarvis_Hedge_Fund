// The offline pack: a saved copy of the app plus the calculators running inside the browser.
//
// The calculators are `backend/rural.py` itself, run by Pyodide (Python compiled to WebAssembly), not
// a second copy written in another language. So an answer given offline is the same answer the server
// would give: same code, same numbers, English and Hindi. The first download needs a connection (about
// 10 MB: the app files, the calculators, and the Python runtime); after that none is needed.
import { create } from "zustand";

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
const FLAG = "jarvis.offline";
const CACHE = "jarvis-offline-v1";            // same name as in public/sw.js

type PackState = "unsupported" | "none" | "installing" | "ready" | "error";
interface Pack { state: PackState; pct: number; msg: string; online: boolean; version: string | null }

const installedVersion = (): string | null => { try { return localStorage.getItem(FLAG); } catch { return null; } };

export const usePack = create<Pack>(() => ({
  state: "serviceWorker" in navigator ? (installedVersion() ? "ready" : "none") : "unsupported",
  pct: 0, msg: "", online: navigator.onLine, version: installedVersion(),
}));
window.addEventListener("online", () => usePack.setState({ online: true }));
window.addEventListener("offline", () => usePack.setState({ online: false }));

let py: any = null;
let loading: Promise<any> | null = null;

function script(src: string): Promise<void> {
  return new Promise((res, rej) => {
    if (document.querySelector(`script[src="${src}"]`)) return res();
    const s = document.createElement("script");
    s.src = src; s.onload = () => res(); s.onerror = () => rej(new Error("could not load " + src));
    document.head.appendChild(s);
  });
}

/** Start the in-browser Python and load the calculators. Cached after the first time. */
async function engine(): Promise<any> {
  if (py) return py;
  loading ??= (async () => {
    await script(PYODIDE + "pyodide.js");
    const p = await (window as any).loadPyodide({ indexURL: PYODIDE });
    const src = await (await fetch("/offline/rural.py")).text();
    p.FS.writeFile("/home/pyodide/rural.py", src);
    p.runPython("import sys, json\nsys.path.insert(0, '/home/pyodide')\nimport rural");
    py = p;
    return p;
  })();
  try { return await loading; } catch (e) { loading = null; throw e; }
}

/** Download everything needed to work with no network. `onStep` reports progress. */
export async function installPack(): Promise<void> {
  const set = (pct: number, msg: string) => usePack.setState({ state: "installing", pct, msg });
  try {
    set(2, "Registering…");
    await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {                       // wait for the worker to take over this page
      await new Promise<void>((r) => { navigator.serviceWorker.addEventListener("controllerchange", () => r(), { once: true }); setTimeout(r, 3000); });
    }
    const list = await (await fetch("/offline/assets")).json();
    const files: { url: string }[] = list.files;
    // Saved straight into the worker's cache, so this does not depend on the worker already being in control.
    const cache = await caches.open(CACHE);
    for (let i = 0; i < files.length; i++) {
      await cache.add(files[i].url);
      set(5 + Math.round((i / files.length) * 25), `App files ${i + 1}/${files.length}`);
    }
    for (const u of ["/", "/rural/schemes?lang=en", "/rural/schemes?lang=hi"]) await cache.add(u);
    set(35, "Python runtime (about 10 MB)…");
    await engine();
    for (const f of ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]) await cache.add(PYODIDE + f);
    set(90, "Checking…");
    const out = JSON.parse(py.runPython("json.dumps(rural.loan_cost(50000, 5, 'per100_month', 10)['yearly_pct'])"));
    if (out !== 60) throw new Error("self-check failed");
    try { localStorage.setItem(FLAG, list.version); } catch { /* storage blocked */ }
    usePack.setState({ state: "ready", pct: 100, msg: "", version: list.version });
  } catch (e) {
    usePack.setState({ state: "error", msg: String((e as Error).message || e) });
  }
}

export const packReady = (): boolean => usePack.getState().state === "ready";

const CALLS: Record<string, (b: any) => [string, unknown[]]> = {
  "/rural/loan": (b) => ["loan_cost", [b.principal, b.rate, b.unit, b.months, b.mode, b.lang]],
  "/rural/scheme": (b) => ["scheme_check", [b.text, b.put, b.get, b.months, b.lang]],
  "/rural/entitlements": (b) => ["entitlements", [b.profile, b.lang]],
  "/rural/readiness": (b) => ["readiness", [b.schemes, b.have, b.lang]],
  "/rural/saving": (b) => ["daily_saving", [b.goal ?? "other", b.target ?? null, b.months ?? null, b.daily ?? null, b.daily_wage ?? null, b.days_per_month ?? 26, b.rate ?? 6.7, 6.0, b.lang]],
  "/rural/shg": (b) => ["shg_summary", [b.ledger, b.as_of ?? null, b.lang]],
  "/rural/shg/lend": (b) => ["shg_can_lend", [b.ledger, b.member, b.amount, b.as_of ?? null, b.lang]],
  "/rural/credit": (b) => ["credit_full", [b.has_credit ?? "none", b.missed ?? "never", b.serious ?? "none", b.utilization ?? "na", b.enquiries ?? "0-1", b.age ?? "na", !!b.informal_only, b.name ?? "", b.lender ?? "", b.wrong ?? "", b.amount ?? 100000, b.years ?? 3, b.good_rate ?? 11, b.poor_rate ?? 16, b.lang]],
  "/rural/hold": (b) => ["hold_or_sell", [b.qty, b.price_now, b.months, b.price_later ?? null, b.storage ?? 0, b.shrink ?? 0, b.handling ?? 0, b.rate ?? 7, b.history ?? "", b.from_month ?? null, b.lang]],
  "/rural/dbt": (b) => ["dbt_full", [b.scheme, b.status, b.linked, b.name_same, b.merged, b.last_used, b.aadhaar_mobile, b.text ?? "", b.name ?? "", b.village ?? "", b.block ?? "", b.bank ?? "", b.lang]],
  "/rural/upi": (b) => ["upi_check", [b.text ?? "", b.lang]],
  "/rural/policy": (b) => ["policy_check", [b.premium, b.pay_years, b.term_years, b.maturity, b.sum_assured ?? null, b.term_quote ?? null, b.text ?? "", b.lang]],
  "/rural/income": (b) => ["income_plan", [b.income, b.monthly_cost, b.one_offs, b.savings, b.borrow_rate ?? 36, b.lang]],
};

async function local(url: string, body?: any): Promise<any> {
  const p = await engine();
  const path = url.split("?")[0];
  if (path === "/rural/schemes") {
    const lang = new URLSearchParams(url.split("?")[1] ?? "").get("lang") === "hi" ? "hi" : "en";
    return { schemes: JSON.parse(p.runPython(`json.dumps([{'id': s['id'], 'name': s['${lang}']} for s in rural.SCHEMES])`)) };
  }
  if (path === "/rural/upi/drills") {
    const lang = new URLSearchParams(url.split("?")[1] ?? "").get("lang") === "hi" ? "hi" : "en";
    return JSON.parse(p.runPython(`json.dumps(rural.upi_drills('${lang}'))`));
  }
  const spec = CALLS[path]?.(body);
  if (!spec) throw new Error("not available offline: " + path);
  p.globals.set("_a", JSON.stringify(spec[1]));
  return JSON.parse(p.runPython(`json.dumps(rural.${spec[0]}(*json.loads(_a)))`));
}

/** Ask the server; if there is no network and the pack is installed, run the same calculator here. */
export async function ruralFetch(url: string, body?: unknown): Promise<any> {
  const useLocal = packReady() && !navigator.onLine;
  if (!useLocal) {
    try {
      const r = await fetch(url, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!r.ok) throw new Error(String(r.status));
      return await r.json();
    } catch (e) {
      if (!packReady()) throw e;                                // not installed: nothing to fall back to
    }
  }
  return local(url, body);
}

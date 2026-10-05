"use client";

import { motion } from "framer-motion";
import {
  ShieldCheck,
  Fingerprint,
  FileText,
  Users,
  TriangleAlert,
  Radar,
} from "lucide-react";
import ShinyText from "@/components/reactbits/shiny-text";

/* ------------------------------------------------------------------ */
/*  Bento capability grid modelled on the reference: three columns —   */
/*  tall verification diagram, two stacked middle cards, tall          */
/*  dashboard panel — all in brand green. The bottom-middle cell is a  */
/*  dashed card recess: the travelling credit card docks INTO it as    */
/*  the visual for the Decision Engine pillar.                         */
/* ------------------------------------------------------------------ */

const fade = (delay = 0) => ({
  initial: { opacity: 0, y: 26 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
  transition: { duration: 0.65, delay },
});

function CellGlow() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_85%_at_20%_112%,rgba(184,241,77,0.17),transparent_58%)]"
    />
  );
}

const CELL =
  "relative flex h-full flex-col overflow-hidden rounded-3xl border border-white/8 bg-[#0b0d0a] p-5 sm:p-6";

/* --- Cell A: verification network diagram -------------------------- */
function VerificationDiagram() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center py-2">
      {/* borrower node */}
      <div className="grid h-16 w-16 place-items-center rounded-full border border-volt/45 bg-volt/10 text-sm font-black text-volt shadow-[0_0_34px_-6px_rgba(184,241,77,0.7)]">
        SOS
      </div>
      <span aria-hidden="true" className="h-7 w-px border-l border-dashed border-volt/35" />
      {/* verification shield */}
      <div className="grid h-12 w-12 place-items-center rounded-2xl border border-white/12 bg-white/[0.05]">
        <ShieldCheck className="h-5 w-5 text-volt" />
      </div>
      {/* fan-out connectors */}
      <svg viewBox="0 0 200 52" className="h-12 w-full max-w-[280px]" fill="none" aria-hidden="true">
        <path d="M100 0v12M100 12 30 52M100 12v40M100 12l70 40" stroke="rgba(184,241,77,0.3)" strokeWidth="1.4" strokeDasharray="3 5" />
        <circle cx="100" cy="12" r="2" fill="rgba(184,241,77,0.7)" />
      </svg>
      {/* evidence nodes */}
      <div className="flex w-full max-w-[280px] items-start justify-between px-1">
        {[
          { icon: Fingerprint, label: "9 Scam scripts" },
          { icon: FileText, label: "8 Specialists" },
          { icon: Users, label: "1930 Helpline" },
        ].map((n) => (
          <div key={n.label} className="flex flex-col items-center gap-2">
            <div className="grid h-12 w-12 place-items-center rounded-xl border border-white/12 bg-white/[0.05]">
              <n.icon className="h-5 w-5 text-zinc-200" />
            </div>
            <span className="text-[9px] font-medium text-zinc-500">{n.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* --- Cell B: risk signal stack -------------------------------------- */
function RiskStack() {
  return (
    <div className="relative mt-1 h-[118px]">
      <div aria-hidden="true" className="absolute inset-x-8 top-0 h-14 rounded-xl border border-white/8 bg-white/[0.03]" />
      <div aria-hidden="true" className="absolute inset-x-4 top-2.5 h-14 rounded-xl border border-white/8 bg-white/[0.04]" />
      <div className="absolute inset-x-0 top-5 flex h-[72px] items-center gap-3 rounded-xl border border-white/12 bg-[#141712] p-3 shadow-[0_18px_40px_-20px_rgba(0,0,0,0.9)]">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-amber-400/25 bg-amber-400/10">
          <TriangleAlert className="h-4 w-4 text-amber-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold text-white">Moneylender APR converted</p>
          <p className="truncate text-[10px] text-zinc-500">
            5 Rs/100 = 60%/yr · KCC saves ₹26,500
          </p>
        </div>
        <Radar className="h-4 w-4 shrink-0 text-volt" />
      </div>
    </div>
  );
}

/* --- Cell D: explainable dashboard mini ----------------------------- */
function DashboardMini() {
  const bars = [
    { label: "Rural & DBT tools", pct: 100 },
    { label: "Scam shield & 1930", pct: 95 },
    { label: "Portfolio X-Ray", pct: 86 },
  ];
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <div className="mt-1 overflow-hidden rounded-xl border border-white/10 bg-[#101310]">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-2.5">
        <span className="h-1.5 w-1.5 rounded-full bg-volt" />
        <p className="text-[10px] font-medium text-zinc-400">JARVIS · 5 Audience Baskets</p>
        <span className="ml-auto rounded-full bg-volt/15 px-2 py-0.5 text-[9px] font-bold text-volt">
          FIVE BASKETS
        </span>
      </div>
      <div className="flex items-center gap-4 p-3.5">
        <svg viewBox="0 0 64 64" className="h-16 w-16 shrink-0 -rotate-90">
          <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
          <circle
            cx="32" cy="32" r={r} fill="none" stroke="#b8f14d" strokeWidth="6"
            strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - 0.86)}
          />
        </svg>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-black leading-none text-white">
            86<span className="text-[10px] font-semibold text-zinc-500"> /100</span>
          </p>
          <div className="mt-2 space-y-1.5">
            {bars.map((b) => (
              <div key={b.label}>
                <div className="flex justify-between text-[8.5px] text-zinc-500">
                  <span>{b.label}</span>
                  <span>{b.pct}</span>
                </div>
                <div className="mt-0.5 h-1 rounded-full bg-white/8">
                  <div className="h-full rounded-full bg-volt/80" style={{ width: `${b.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="flex gap-1.5 px-3.5 pb-3">
        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[8.5px] text-zinc-400">English &amp; हिन्दी</span>
        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[8.5px] text-zinc-400">532 Verified Tests</span>
      </div>
    </div>
  );
}

/* --- Cell C: audit ledger visual --------------------------------- */
function AuditLedgerVisual() {
  return (
    <div className="relative flex flex-1 flex-col justify-center space-y-2 py-1">
      <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-[10px]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-volt" />
          <span className="font-mono text-zinc-300">block_#412</span>
        </div>
        <span className="font-mono text-[9px] text-zinc-500">hash: 9f8a...3c21</span>
        <span className="rounded bg-volt/15 px-1.5 py-0.5 text-[8.5px] font-bold text-volt">LINKED</span>
      </div>

      <div className="flex items-center justify-center">
        <span className="h-3 w-px border-l border-dashed border-volt/40" />
      </div>

      <div className="flex items-center justify-between rounded-xl border border-volt/25 bg-volt/[0.05] px-3 py-2 text-[10px] shadow-[0_0_20px_-5px_rgba(184,241,77,0.15)]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-volt animate-ping-soft" />
          <span className="font-mono font-semibold text-white">block_#413</span>
        </div>
        <span className="font-mono text-[9px] text-zinc-400">prev: 9f8a...3c21</span>
        <span className="rounded bg-volt px-1.5 py-0.5 text-[8.5px] font-bold text-[#101502]">VERIFIED</span>
      </div>

      <p className="pt-1 text-center text-[9px] font-bold tracking-[0.25em] text-volt/60">
        ARITHMETIC APPROVES · NEVER AN LLM
      </p>
    </div>
  );
}

/* -------------------------------------------------------------------- */

export default function Pillars() {
  return (
    <section
      id="pillars"
      className="relative flex min-h-[100svh] flex-col overflow-hidden bg-coal"
    >
      {/* faint grid lines + green ambience + diamonds */}
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.022)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.022)_1px,transparent_1px)] bg-[size:76px_76px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 left-1/2 h-[420px] w-[760px] -translate-x-1/2 rounded-full bg-volt/[0.06] blur-[140px]"
      />
      <span aria-hidden="true" className="absolute left-[8%] top-[12%] h-3 w-3 rotate-45 border border-volt/20" />
      <span aria-hidden="true" className="absolute right-[10%] top-[40%] h-4 w-4 rotate-45 border border-volt/15" />
      <span aria-hidden="true" className="absolute bottom-[10%] left-[45%] h-2.5 w-2.5 rotate-45 bg-volt/10" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col px-5 py-10 sm:px-8 sm:py-12">
        {/* header */}
        <div className="text-center">
          <motion.p {...fade()} className="text-xs font-semibold tracking-[0.3em]">
            <ShinyText
              text="· AUDIENCE-LED SCOPE"
              className="font-semibold text-volt/90"
              speed={4}
            />
          </motion.p>
          <motion.h2
            {...fade(0.06)}
            className="mx-auto mt-3 max-w-3xl font-display text-3xl font-semibold tracking-tight text-white sm:text-5xl"
          >
            A guard, guide, and calculator for everyday money.
          </motion.h2>
        </div>

        {/* bento grid */}
        <div className="mt-8 grid flex-1 gap-4 sm:gap-5 lg:grid-cols-3 lg:grid-rows-2">
          {/* A — verification (tall) */}
          <motion.article {...fade(0.1)} className={CELL + " lg:row-span-2"}>
            <CellGlow />
            <VerificationDiagram />
            <h3 className="relative mt-4 text-base font-bold leading-snug text-white">
              Scam Protection &amp; 1930 Recovery Coach
            </h3>
            <p className="relative mt-2 text-xs leading-relaxed text-zinc-400">
              Nine scam scripts, an 8-specialist tip checker, scam-call
              rehearsal, and an emergency recovery coach guiding the crucial
              first hour through the 1930 national helpline.
            </p>
          </motion.article>

          {/* B — risk & fraud */}
          <motion.article {...fade(0.18)} className={CELL}>
            <CellGlow />
            <RiskStack />
            <h3 className="relative mt-5 text-base font-bold leading-snug text-white">
              Rural Money Tools &amp; Group Ledger
            </h3>
            <p className="relative mt-2 text-xs leading-relaxed text-zinc-400">
              Converts moneylender quotes (&quot;5 Rs per 100&quot;) to a true
              60% yearly rate, tracks DBT government schemes, checks UPI
              safety, and runs offline self-help group ledgers.
            </p>
          </motion.article>

          {/* C — decision engine */}
          <motion.article
            {...fade(0.26)}
            className={CELL + " lg:col-start-2 lg:row-start-2"}
          >
            <CellGlow />
            <AuditLedgerVisual />
            <h3 className="relative mt-4 text-base font-bold leading-snug text-white">
              Govern, Risk Firewall &amp; Tamper-Evident Ledger
            </h3>
            <p className="relative mt-2 text-xs leading-relaxed text-zinc-400">
              A deterministic risk engine checking trades against limits,
              rebalance simulator, and hash-chained SQLite ledger. Every decision
              carries the previous entry&apos;s fingerprint.
            </p>
          </motion.article>

          {/* D — explainable dashboard (tall) */}
          <motion.article
            {...fade(0.34)}
            className={CELL + " lg:col-start-3 lg:row-start-1 lg:row-span-2"}
          >
            <CellGlow />
            <DashboardMini />
            <div className="flex-1" />
            <h3 className="relative mt-4 text-base font-bold leading-snug text-white">
              Bilingual Assistant, WhatsApp &amp; Research Desk
            </h3>
            <p className="relative mt-2 text-xs leading-relaxed text-zinc-400">
              Ask in Hindi or English by voice, text, or WhatsApp simulator.
              Features a 25-point stock research desk, 32 plain learning
              topics, and five tailored starting baskets.
            </p>
          </motion.article>
        </div>
      </div>
    </section>
  );
}

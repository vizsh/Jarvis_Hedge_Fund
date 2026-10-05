"use client";

import { motion } from "framer-motion";
import {
  BadgeCheck,
  CircleAlert,
  FileText,
  Gauge,
  ScrollText,
  ArrowUpRight,
} from "lucide-react";
import TiltedCard from "@/components/reactbits/tilted-card";
import ShinyText from "@/components/reactbits/shiny-text";

const PROMISES = [
  {
    icon: FileText,
    title: "The model never writes a number",
    desc: "Numbers come from deterministic code and dated public data. An optional local model only picks from a fixed list.",
  },
  {
    icon: Gauge,
    title: "Protect before money moves",
    desc: "Spot scams, predatory 60% loans, or missed DBT benefits before they cost money; with immediate 1930 recovery steps.",
  },
  {
    icon: BadgeCheck,
    title: "Every number is a door",
    desc: "Tap any figure to see the arithmetic behind it, in plain English or हिन्दी — no guesswork, no hallucinated math.",
  },
  {
    icon: ScrollText,
    title: "Hash-chained audit record",
    desc: "Every decision carries the previous entry's cryptographic fingerprint. 532 automated tests verify every calculator.",
  },
];

const POSITIVES = [
  "Moneylender '5 Rs / 100' converted to 60%/yr APR",
  "Formal KCC loan at 7% saves ₹26,500 in yearly interest",
  "DBT PM-Kisan instalment verified and on schedule",
  "9 scam scripts & 1930 recovery active in Hindi & English",
];

const RISKS = [
  "Moneylender charges ₹30,000 yearly interest on ₹50,000",
  "One mutual fund charges 2% — ₹2.1L drag over 20 years",
];

function ScoreRing() {
  const r = 58;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative h-36 w-36 shrink-0">
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="10"
        />
        <motion.circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke="#b8f14d"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          whileInView={{ strokeDashoffset: c * (1 - 0.86) }}
          viewport={{ once: true }}
          transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-4xl font-black tracking-tight text-white">86</p>
        <p className="text-[10px] font-semibold tracking-[0.18em] text-zinc-500">
          / 100
        </p>
      </div>
    </div>
  );
}

function DashboardMock() {
  return (
    <div className="relative">
      {/* orange ambience behind panel */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-8 rounded-[48px] bg-orange-500/20 blur-[70px]"
      />

      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="relative"
      >
        <TiltedCard
          rotateAmplitude={5}
          glareOpacity={0.1}
          className="overflow-hidden rounded-3xl"
        >
          <div className="relative overflow-hidden rounded-3xl border border-white/12 bg-[#141619] shadow-2xl shadow-black/70">
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-white/8 px-5 py-3.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
          <p className="ml-3 text-xs font-medium text-zinc-500">
            JARVIS · Everyday Money Engine
          </p>
          <span className="ml-auto rounded-full bg-volt/15 px-2.5 py-1 text-[10px] font-bold text-volt">
            THREE PROMISES
          </span>
        </div>

        <div className="p-5 sm:p-6">
          {/* borrower header */}
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <ScoreRing />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-volt to-volt-deep text-xs font-bold text-[#101502]">
                  FL
                </span>
                <div>
                  <p className="text-sm font-bold text-white">Farmer Loan vs Bank Credit</p>
                  <p className="text-[11px] text-zinc-500">
                    ₹50,000 principal · 12-month tenure
                  </p>
                </div>
              </div>
              <div className="mt-3.5 flex flex-wrap gap-1.5">
                {["60% Moneylender APR", "7% Formal KCC", "1930 Active"].map(
                  (chip) => (
                    <span
                      key={chip}
                      className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-medium text-zinc-300"
                    >
                      {chip}
                    </span>
                  ),
                )}
                <span className="rounded-full bg-volt px-2.5 py-1 text-[10px] font-bold text-[#101502]">
                  HEALTHY
                </span>
              </div>
            </div>
          </div>

          {/* signals */}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-[10px] font-bold tracking-[0.2em] text-volt">
                WHAT IS WORKING
              </p>
              <ul className="mt-3 space-y-2.5">
                {POSITIVES.map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <BadgeCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-volt" />
                    <span className="text-[11px] leading-relaxed text-zinc-300">
                      {s}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <p className="text-[10px] font-bold tracking-[0.2em] text-amber-400">
                WHAT TO FIX
              </p>
              <ul className="mt-3 space-y-2.5">
                {RISKS.map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                    <span className="text-[11px] leading-relaxed text-zinc-300">
                      {s}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-4 rounded-xl bg-white/[0.04] px-3 py-2 text-[10px] leading-relaxed text-zinc-400">
                Why this matters: &apos;5 rupees per hundred&apos; means 60% per year —
                nearly ten times what a formal bank or KCC loan costs.
              </p>
            </div>
          </div>

          {/* recommendation footer */}
          <div className="mt-5 flex flex-col gap-3 rounded-2xl border border-volt/20 bg-volt/[0.06] p-4 sm:flex-row sm:items-center">
            <div className="flex-1">
              <p className="text-[10px] font-bold tracking-[0.2em] text-volt">
                PLAIN ARITHMETIC · ZERO GUESSWORK
              </p>
              <p className="mt-1 text-sm font-bold text-white">
                Switch to Formal Bank Loan · Save ₹26,500 in Year 1
              </p>
              <p className="mt-0.5 text-[11px] text-zinc-400">
                Formal KCC at 7% vs informal 60% APR — the arithmetic is on the
                next screen.
              </p>
            </div>
            <button className="group flex items-center justify-center gap-1.5 rounded-full bg-volt px-5 py-2.5 text-xs font-bold text-[#101502] transition hover:bg-volt-soft">
              Show the arithmetic
              <ArrowUpRight className="h-3.5 w-3.5 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
            </button>
          </div>
        </div>
          </div>
        </TiltedCard>
      </motion.div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

export default function Explainable() {
  return (
    <section
      id="explainable"
      className="relative flex min-h-[100svh] items-center overflow-hidden bg-coal"
    >
      <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:gap-12 xl:gap-16">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-xs font-bold tracking-[0.3em]"
          >
            <ShinyText
              text="THE THREE PROMISES"
              className="font-bold text-orange-400/85"
              speed={4}
            />
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.06 }}
            className="mt-4 text-3xl font-black tracking-tight text-white sm:text-4xl"
          >
            Protect. Explain.
            <br />
            Stay{" "}
            <span className="bg-gradient-to-b from-orange-300 to-orange-600 bg-clip-text text-transparent">
              honest.
            </span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.12 }}
            className="mt-5 text-sm leading-relaxed text-zinc-400 sm:text-base"
          >
            JARVIS answers money questions plainly in Hindi or English. The
            numbers come from code and dated public data, never from a language
            model. An optional local model only picks which tool to run from a
            closed list — it never writes a figure. Nothing says buy, sell or hold.
          </motion.p>

          <div className="mt-7 grid grid-cols-2 gap-x-4 gap-y-5">
            {PROMISES.map((p, i) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.1 + i * 0.06 }}
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-orange-500/25 bg-orange-500/10 text-orange-400">
                  <p.icon className="h-4 w-4" />
                </div>
                <h3 className="mt-2.5 text-[13px] font-bold leading-snug text-white">{p.title}</h3>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
                  {p.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        <DashboardMock />
      </div>
    </section>
  );
}

"use client";

import { motion } from "framer-motion";
import { ScanFace, BrainCircuit, GaugeCircle, HandCoins } from "lucide-react";
import CountUp from "@/components/reactbits/count-up";
import ShinyText from "@/components/reactbits/shiny-text";

const STEPS = [
  {
    n: "01",
    icon: ScanFace,
    title: "Ask",
    desc: "Type, speak, or message on WhatsApp — in English or हिन्दी. Ask about a moneylender loan, a suspicious call, or a DBT benefit.",
  },
  {
    n: "02",
    icon: BrainCircuit,
    title: "Route",
    desc: "The understanding layer reads sentence meaning across 5 paths: scam scripts, company facts, calculators, checked text, or tours.",
  },
  {
    n: "03",
    icon: GaugeCircle,
    title: "Compute",
    desc: "Deterministic code computes exact figures against dated public data — yearly loan APR, fee drag, overlap, runway. Zero AI guesses.",
  },
  {
    n: "04",
    icon: HandCoins,
    title: "Explain",
    desc: "Structured cards show the answer with its working, rupees, steps, and confidence marks — tailored to one of five audience baskets.",
  },
];

const STATS = [
  { to: 532, suffix: "", label: "automated tests across 35 files" },
  { to: 100, suffix: "%", label: "local & private — no data sold, rural tools always free" },
  { to: 5, suffix: " baskets", label: "starting baskets for banks, farmers, SHGs, investors & pitch" },
  { to: 0, suffix: "", label: "numbers ever produced by a language model" },
];

export default function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative flex min-h-[100svh] items-center overflow-hidden bg-ink"
    >
      {/* faint green ambience */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 right-0 h-[420px] w-[620px] rounded-full bg-volt/8 blur-[120px]"
      />

      <div className="relative z-10 mx-auto w-full max-w-7xl px-5 py-14 sm:px-8 sm:py-16">
        <div className="max-w-3xl">
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-xs font-bold tracking-[0.3em]"
          >
            <ShinyText
              text="HOW IT WORKS"
              className="font-bold text-volt/85"
              speed={4}
            />
          </motion.p>
          <motion.h2
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.06 }}
            className="mt-3 text-3xl font-black tracking-tight text-white sm:text-4xl"
          >
            From an everyday question to plain arithmetic, in four steps.
          </motion.h2>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: i * 0.07 }}
              className="group relative overflow-hidden rounded-2xl border border-white/8 bg-white/[0.03] p-5 transition duration-300 hover:border-volt/35 hover:bg-white/[0.05]"
            >
              <p className="pointer-events-none absolute -right-1 -top-3 select-none text-[64px] font-black leading-none text-white/[0.05] transition group-hover:text-volt/10">
                {s.n}
              </p>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-volt/25 bg-volt/10 text-volt">
                  <s.icon className="h-4.5 w-4.5" />
                </div>
                <h3 className="text-base font-bold text-white">{s.title}</h3>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-zinc-400">
                {s.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* stats band */}
        <motion.div
          initial={{ opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7 }}
          className="mt-10 grid grid-cols-2 gap-y-8 rounded-3xl border border-white/8 bg-white/[0.02] px-6 py-8 lg:grid-cols-4"
        >
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="bg-gradient-to-b from-white to-zinc-400 bg-clip-text text-3xl font-black tracking-tight text-transparent sm:text-4xl">
                <CountUp to={s.to} suffix={s.suffix} duration={2} />
              </p>
              <p className="mx-auto mt-2 max-w-[200px] text-xs leading-relaxed text-zinc-500">
                {s.label}
              </p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

"use client";

import { motion } from "framer-motion";
import {
  ArrowUpRight,
  Linkedin,
  Twitter,
  Youtube,
  Github,
  Heart,
} from "lucide-react";

const SOCIALS = [
  { icon: Linkedin, label: "LinkedIn" },
  { icon: Twitter, label: "Twitter/X" },
  { icon: Youtube, label: "YouTube" },
  { icon: Github, label: "GitHub" },
];

const HELPFUL = [
  "Five Baskets",
  "Scam Protection (1930)",
  "Rural Money Tools",
  "WhatsApp Simulator",
  "Govern & Audit",
];

export default function SiteFooter() {
  return (
    <footer
      id="contact"
      className="relative overflow-hidden bg-[#111214]"
    >
      <div className="mx-auto max-w-7xl px-5 pt-16 sm:px-8 sm:pt-24">
        {/* top grid */}
        <div className="grid gap-12 lg:grid-cols-2">
          {/* left: big CTA */}
          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7 }}
          >
            <h2 className="text-4xl font-black leading-[1.05] tracking-tight text-white sm:text-6xl">
              Money,
              <br />
              Plainly
              <span className="text-volt">.</span>
            </h2>
            <a
              href="https://github.com/vizsh/Jarvis_Hedge_Fund"
              className="group mt-8 inline-flex items-center gap-3 rounded-2xl bg-[#1b1d22] py-2.5 pl-5 pr-2.5 text-sm font-semibold text-white ring-1 ring-white/10 transition hover:bg-[#22252b]"
            >
              Run It Locally
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-volt text-[#101502] transition group-hover:bg-volt-soft">
                <ArrowUpRight className="h-4 w-4" />
              </span>
            </a>
          </motion.div>

          {/* right: columns */}
          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-2"
          >
            <div>
              <p className="text-sm font-bold text-white">Runs on</p>
              <p className="mt-3 text-sm text-zinc-400">Your machine</p>
              <p className="text-sm text-zinc-400">localhost:3000</p>
              <p className="mt-6 text-sm font-bold text-white">Social</p>
              <div className="mt-3 space-y-2">
                {SOCIALS.map((s) => (
                  <a
                    key={s.label}
                    href="#contact"
                    className="group flex items-center gap-2 text-sm text-zinc-400 transition hover:text-white"
                  >
                    <s.icon className="h-4 w-4 text-volt transition group-hover:text-volt-soft" />
                    {s.label}
                  </a>
                ))}
              </div>
            </div>
            <div className="sm:text-right">
              <p className="text-sm font-bold text-white">Project</p>
              <a
                href="https://github.com/vizsh/Jarvis_Hedge_Fund"
                className="mt-3 block text-sm text-zinc-400 transition hover:text-white"
              >
                github.com/vizsh
              </a>
              <p className="text-sm text-zinc-400">Jarvis_Hedge_Fund</p>
              <p className="mt-6 text-sm font-bold text-white">Architecture &amp; Scope</p>
              <div className="mt-3 space-y-2">
                {HELPFUL.map((l) => (
                  <a
                    key={l}
                    href="#pillars"
                    className="block text-sm text-zinc-400 transition hover:text-white"
                  >
                    {l}
                  </a>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* divider + bottom bar */}
        <div className="mt-14 border-t border-white/10 py-6">
          <div className="flex flex-col items-center justify-between gap-4 text-xs text-zinc-500 sm:flex-row">
            <p>© JARVIS 2026 · money, plainly</p>
            <p className="flex items-center gap-1.5">
              <Heart className="h-3.5 w-3.5 fill-volt text-volt" />
              Not financial advice · Describes and explains · 0 numbers from AI
            </p>
            <p className="flex items-center gap-2">
              Built with
              <span className="font-signature text-2xl leading-none text-zinc-300">
                JARVIS
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* green duotone block with giant cropped brand typography
          (the studiogram orange block — now in brand green) */}
      <div className="px-2 pb-2 sm:px-3 sm:pb-3">
        <div className="relative h-[240px] overflow-hidden rounded-[20px] bg-gradient-to-br from-[#9ade33] via-[#8fce2b] to-[#79b71f] sm:h-[360px] sm:rounded-[26px]">
          {/* duotone texture layers */}
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_20%,rgba(255,255,255,0.35),transparent_55%),radial-gradient(ellipse_at_20%_90%,rgba(0,0,0,0.35),transparent_60%)]"
          />
          <p
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-[22%] select-none whitespace-nowrap text-center font-black leading-[0.8] tracking-[-0.05em] text-[#101402]/55 [font-size:18vw]"
          >
            JARVIS
          </p>
        </div>
      </div>
    </footer>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  ChevronDown,
  Check,
  Play,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { WORLD_DOTS_BASE, WORLD_DOTS_ACCENT } from "./world-dots";
import DotGrid from "@/components/reactbits/dot-grid";
import BlurText from "@/components/reactbits/blur-text";
import ShinyText from "@/components/reactbits/shiny-text";
import CountUp from "@/components/reactbits/count-up";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

type Profile = {
  id: number;
  name: string;
  initials: string;
  kind: string;
  score: number;
  signals: string;
  evidence: string;
  terms: string;
};

const PROFILES: Profile[] = [
  {
    id: 0,
    name: "Farmer Loan Check",
    initials: "FL",
    kind: "Moneylender vs Bank",
    score: 86,
    signals: "'5 Rs per 100' quote · ₹50,000",
    evidence: "Uncovers 60%/yr APR · KCC offers 7%",
    terms: "Save ₹26,500 interest with formal credit",
  },
  {
    id: 1,
    name: "Scam Shield & 1930",
    initials: "SS",
    kind: "Fake Police / Digital Arrest",
    score: 95,
    signals: "8 specialist analysis · high threat",
    evidence: "9 scam scripts checked · 1930 helpline",
    terms: "First-hour response saves stolen funds",
  },
  {
    id: 2,
    name: "Retail Fund X-Ray",
    initials: "RX",
    kind: "2 Mutual Funds · ₹6.2L SIP",
    score: 48,
    signals: "Fee drag & overlap analysis",
    evidence: "2% fee eats 33% of 20yr growth",
    terms: "Switch saves ₹2,10,000 in fee drag",
  },
];

const NAV_LINKS = [
  { label: "Home", href: "#home", active: true },
  { label: "Five Baskets", href: "#pillars", active: false },
  { label: "Three Promises", href: "#explainable", active: false },
  { label: "The Problem", href: "#problem", active: false },
  { label: "How It Works", href: "#how-it-works", active: false },
];

/* ------------------------------------------------------------------ */
/*  Brand mark                                                         */
/* ------------------------------------------------------------------ */

function LogoMark({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <path
        d="M20 2 36 10v10c0 9.2-6.6 15.6-16 18C10.6 35.6 4 29.2 4 20V10L20 2Z"
        fill="#b8f14d"
      />
      <path
        d="M20 8.5 29.5 13v7c0 5.9-4.1 10.1-9.5 11.9C14.1 30.1 10 25.9 10 20v-7L20 8.5Z"
        fill="#16181d"
      />
      <circle cx="20" cy="19.5" r="4" fill="#b8f14d" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Velopay-style diagonal light beams from the top corners            */
/* ------------------------------------------------------------------ */

function LightBeams() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {/* broad corner washes */}
      <div className="absolute -left-32 -top-56 h-[640px] w-[540px] rotate-[33deg] bg-gradient-to-b from-white/[0.10] via-white/[0.03] to-transparent blur-3xl" />
      <div className="absolute -right-32 -top-56 h-[640px] w-[540px] -rotate-[33deg] bg-gradient-to-b from-white/[0.10] via-white/[0.03] to-transparent blur-3xl" />
      {/* left streaks */}
      <div className="absolute -top-28 left-[1%] h-[440px] w-[112px] rotate-[31deg] bg-gradient-to-b from-white/[0.14] to-transparent blur-2xl" />
      <div className="absolute -top-44 left-[10%] h-[480px] w-[54px] rotate-[29deg] bg-gradient-to-b from-white/[0.10] to-transparent blur-2xl" />
      <div className="absolute -top-36 left-[19%] h-[380px] w-[26px] rotate-[27deg] bg-gradient-to-b from-white/[0.08] to-transparent blur-xl" />
      {/* right streaks */}
      <div className="absolute -top-28 right-[1%] h-[440px] w-[112px] -rotate-[31deg] bg-gradient-to-b from-white/[0.14] to-transparent blur-2xl" />
      <div className="absolute -top-44 right-[10%] h-[480px] w-[54px] -rotate-[29deg] bg-gradient-to-b from-white/[0.10] to-transparent blur-2xl" />
      <div className="absolute -top-36 right-[19%] h-[380px] w-[26px] -rotate-[27deg] bg-gradient-to-b from-white/[0.08] to-transparent blur-xl" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Glowing globe network art (dotted world map + horizon arcs)        */
/* ------------------------------------------------------------------ */

function GlobeArt() {
  return (
    <svg
      viewBox="0 0 1600 760"
      preserveAspectRatio="xMidYMax slice"
      className="pointer-events-none absolute bottom-0 left-1/2 w-[1600px] max-w-none -translate-x-1/2"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="gGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#b8f14d" stopOpacity="0.30" />
          <stop offset="55%" stopColor="#b8f14d" stopOpacity="0.10" />
          <stop offset="100%" stopColor="#b8f14d" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="gBloomCore" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#e9ffb0" stopOpacity="0.5" />
          <stop offset="45%" stopColor="#c6f96a" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#b8f14d" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="gArc" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#b8f14d" stopOpacity="0" />
          <stop offset="0.35" stopColor="#b8f14d" stopOpacity="0.9" />
          <stop offset="0.5" stopColor="#e7ffa3" />
          <stop offset="0.65" stopColor="#b8f14d" stopOpacity="0.9" />
          <stop offset="1" stopColor="#b8f14d" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="gPlanet" cx="50%" cy="8%" r="90%">
          <stop offset="0%" stopColor="#131a09" />
          <stop offset="45%" stopColor="#0c1008" />
          <stop offset="100%" stopColor="#070906" />
        </radialGradient>
        <linearGradient id="gTerminator" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0" />
          <stop offset="0.45" stopColor="#000" stopOpacity="0.55" />
          <stop offset="0.72" stopColor="#040604" stopOpacity="0.4" />
          <stop offset="1" stopColor="#d7ff8a" stopOpacity="0.07" />
        </linearGradient>
        <linearGradient id="gBeam" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#d7ff8a" stopOpacity="0.55" />
          <stop offset="1" stopColor="#d7ff8a" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="gMaskFade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" />
          <stop offset="0.55" stopColor="#999" />
          <stop offset="1" stopColor="#111" />
        </linearGradient>
        <linearGradient id="gMaskSoft" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" />
          <stop offset="0.55" stopColor="#e8e8e8" />
          <stop offset="1" stopColor="#777" />
        </linearGradient>
        <mask id="mDots">
          <rect x="0" y="0" width="1600" height="760" fill="url(#gMaskFade)" />
        </mask>
        <mask id="mSoft">
          <rect x="0" y="0" width="1600" height="760" fill="url(#gMaskSoft)" />
        </mask>
        <pattern id="gDots" width="24" height="24" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.4" fill="#9ecb4f" fillOpacity="0.3" />
        </pattern>
        <clipPath id="planetClip">
          <ellipse cx="800" cy="1760" rx="1180" ry="1330" />
        </clipPath>
        <filter id="fBlur40" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="42" />
        </filter>
        <filter id="fBlur24" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="24" />
        </filter>
        <filter id="fBlur8" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="8" />
        </filter>
      </defs>

      {/* ambient bloom behind the planet */}
      <ellipse
        cx="800"
        cy="500"
        rx="880"
        ry="380"
        fill="url(#gGlow)"
        filter="url(#fBlur40)"
      />

      {/* planet base + fine texture */}
      <ellipse cx="800" cy="1760" rx="1180" ry="1330" fill="url(#gPlanet)" />
      <ellipse
        cx="800"
        cy="1760"
        rx="1180"
        ry="1330"
        fill="url(#gDots)"
        mask="url(#mDots)"
      />

      {/* dotted world map (auto-generated), drawn twice so the rotation loops */}
      <g clipPath="url(#planetClip)" mask="url(#mSoft)">
        <g className="globe-spin">
          {[0, 1600].map((offset) => (
            <g key={offset} transform={`translate(${offset} 0)`}>
              <path d={WORLD_DOTS_BASE} fill="#8fbe45" fillOpacity="0.5" />
              <path d={WORLD_DOTS_ACCENT} fill="#d7ff8a" fillOpacity="0.85" />
            </g>
          ))}
        </g>

        {/* day/night terminator sweeping across the surface */}
        <g className="globe-terminator">
          <rect
            x="0"
            y="380"
            width="620"
            height="460"
            fill="url(#gTerminator)"
          />
        </g>
      </g>

      {/* horizon glow + crisp arc */}
      <ellipse
        cx="800"
        cy="1760"
        rx="1180"
        ry="1330"
        fill="none"
        stroke="#b8f14d"
        strokeWidth="14"
        opacity="0.22"
        filter="url(#fBlur8)"
      />
      <ellipse
        cx="800"
        cy="1760"
        rx="1180"
        ry="1330"
        fill="none"
        stroke="url(#gArc)"
        strokeWidth="2.5"
      />

      {/* tight bright bloom at the crest */}
      <ellipse
        cx="800"
        cy="448"
        rx="330"
        ry="105"
        fill="url(#gBloomCore)"
        filter="url(#fBlur24)"
      />

      {/* vertical light shafts rising from the horizon */}
      <g filter="url(#fBlur8)" opacity="0.5">
        <rect x="396" y="240" width="70" height="258" fill="url(#gBeam)" />
        <rect x="596" y="172" width="64" height="264" fill="url(#gBeam)" />
        <rect x="772" y="168" width="56" height="264" fill="url(#gBeam)" />
        <rect x="940" y="172" width="64" height="264" fill="url(#gBeam)" />
        <rect x="1134" y="240" width="70" height="258" fill="url(#gBeam)" />
      </g>

      {/* connection arcs over the horizon */}
      <g fill="none" strokeLinecap="round">
        <g stroke="#b8f14d" opacity="0.2" strokeWidth="5" filter="url(#fBlur8)">
          <path d="M320 545 Q 610 300 900 435" />
          <path d="M520 468 Q 810 240 1100 474" />
          <path d="M700 435 Q 990 262 1280 545" />
          <path d="M320 545 Q 510 382 700 435" />
          <path d="M900 435 Q 1090 382 1280 545" />
        </g>
        <g stroke="#c9f06d" strokeWidth="1.4">
          <path d="M320 545 Q 610 300 900 435" opacity="0.5" />
          <path d="M520 468 Q 810 240 1100 474" opacity="0.55" />
          <path d="M700 435 Q 990 262 1280 545" opacity="0.5" />
          <path d="M320 545 Q 510 382 700 435" opacity="0.35" />
          <path d="M900 435 Q 1090 382 1280 545" opacity="0.35" />
        </g>
      </g>

      {/* city nodes on the horizon */}
      {[
        { x: 320, y: 545 },
        { x: 520, y: 468 },
        { x: 700, y: 435 },
        { x: 900, y: 435 },
        { x: 1100, y: 474 },
        { x: 1280, y: 545 },
      ].map((p, i) => (
        <g key={i}>
          <circle
            cx={p.x}
            cy={p.y}
            r="12"
            fill="#d7ff8a"
            opacity="0.3"
            filter="url(#fBlur8)"
          />
          <circle cx={p.x} cy={p.y} r="4.2" fill="#eeffc4">
            {i % 2 === 0 && (
              <animate
                attributeName="opacity"
                values="1;0.55;1"
                dur={`${2.8 + i * 0.5}s`}
                repeatCount="indefinite"
              />
            )}
          </circle>
        </g>
      ))}

      {/* network nodes on the planet surface */}
      <g stroke="#b8f14d" strokeWidth="1.1" opacity="0.3" fill="none">
        <path d="M520 585 Q 640 540 770 555" />
        <path d="M770 555 Q 910 562 1035 600" />
        <path d="M655 675 Q 795 715 935 682" />
        <path d="M405 662 Q 465 618 520 585" />
        <path d="M1035 600 Q 1110 630 1180 672" />
      </g>
      {[
        { x: 520, y: 585 },
        { x: 770, y: 555 },
        { x: 1035, y: 600 },
        { x: 655, y: 675 },
        { x: 935, y: 682 },
        { x: 405, y: 662 },
        { x: 1180, y: 672 },
      ].map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="7" fill="#b8f14d" opacity="0.15" />
          <circle cx={n.x} cy={n.y} r="3" fill="#d7ff8a">
            {i % 3 === 0 && (
              <animate
                attributeName="r"
                values="3;5.4;3"
                dur={`${2.6 + i * 0.4}s`}
                repeatCount="indefinite"
              />
            )}
          </circle>
        </g>
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Portfolio X-ray widget (mirrors the currency converter)            */
/* ------------------------------------------------------------------ */

function TrustCheckWidget() {
  const [profile, setProfile] = useState<Profile>(PROFILES[0]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [phase, setPhase] = useState<"idle" | "analyzing" | "done">("idle");
  const [display, setDisplay] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  useEffect(() => {
    if (phase !== "done") return;
    const target = profile.score;
    const start = performance.now();
    const dur = 950;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(eased * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase, profile.score]);

  const tone =
    profile.score >= 75
      ? {
          badge: "bg-volt text-[#101502]",
          bar: "bg-volt",
          label: "HEALTHY",
        }
      : profile.score >= 60
        ? {
            badge: "bg-amber-400 text-[#231a02]",
            bar: "bg-amber-400",
            label: "NEEDS A LOOK",
          }
        : {
            badge: "bg-red-500/90 text-white",
            bar: "bg-red-500",
            label: "AT RISK",
          };

  const run = () => {
    if (phase === "analyzing") return;
    setPhase("analyzing");
    setDisplay(0);
    timer.current = setTimeout(() => setPhase("done"), 1500);
  };

  const select = (p: Profile) => {
    setProfile(p);
    setMenuOpen(false);
    setPhase("idle");
    setDisplay(0);
  };

  return (
    <div className="w-full max-w-[350px] rounded-3xl border border-white/10 bg-[#1b1e24]/90 p-5 shadow-2xl shadow-black/60 backdrop-blur-md">
      {/* Portfolio row */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-medium tracking-[0.14em] text-zinc-400">
          AUDIENCE BASKET
        </p>
        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 text-xs font-medium text-zinc-200 ring-1 ring-white/10 transition hover:bg-white/10"
            aria-haspopup="listbox"
            aria-expanded={menuOpen}
          >
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-volt text-[8px] font-bold text-[#101502]">
              {profile.initials}
            </span>
            {profile.kind}
            <ChevronDown className="h-3 w-3 text-zinc-400" />
          </button>
          {menuOpen && (
            <>
              <button
                className="fixed inset-0 z-10 cursor-default"
                aria-label="Close menu"
                onClick={() => setMenuOpen(false)}
              />
              <div
                role="listbox"
                className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-2xl border border-white/10 bg-[#22262e] p-1.5 shadow-2xl shadow-black/70"
              >
                {PROFILES.map((p) => (
                  <button
                    key={p.id}
                    role="option"
                    aria-selected={p.id === profile.id}
                    onClick={() => select(p)}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left transition hover:bg-white/10 ${
                      p.id === profile.id ? "bg-white/10" : ""
                    }`}
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-volt to-volt-deep text-[10px] font-bold text-[#101502]">
                      {p.initials}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-semibold text-white">
                        {p.name}
                      </span>
                      <span className="block text-[10px] text-zinc-400">
                        {p.kind}
                      </span>
                    </span>
                    {p.id === profile.id && (
                      <Check className="ml-auto h-3.5 w-3.5 text-volt" />
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <p className="mt-1.5 text-2xl font-bold tracking-tight text-white">
        {profile.name}
      </p>

      {/* divider with arrow */}
      <div className="relative my-4">
        <div className="h-px bg-white/10" />
        <span className="absolute left-1/2 top-1/2 flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-[#22262e]">
          <ArrowRight className="h-3.5 w-3.5 rotate-90 text-zinc-400" />
        </span>
      </div>

      {/* Score row */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-medium tracking-[0.14em] text-zinc-400">
          TRUST &amp; SAFETY INDEX
        </p>
        {phase === "done" && (
          <span
            className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wide ${tone.badge}`}
          >
            {tone.label}
          </span>
        )}
      </div>

      {phase === "analyzing" ? (
        <p className="mt-1.5 flex items-center gap-2 text-2xl font-bold tracking-tight text-zinc-300">
          <Loader2 className="h-5 w-5 animate-spin text-volt" />
          Analyzing signals…
        </p>
      ) : phase === "done" ? (
        <p className="mt-1.5 text-2xl font-bold tracking-tight text-white">
          {display}
          <span className="text-base font-semibold text-zinc-500"> /100</span>
        </p>
      ) : (
        <p className="mt-1.5 text-2xl font-bold tracking-tight text-zinc-600">
          — —<span className="text-base font-semibold text-zinc-700"> /100</span>
        </p>
      )}

      {/* score bar */}
      <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-[width] duration-200 ease-out ${tone.bar} ${
            phase !== "done" ? "opacity-30" : ""
          }`}
          style={{ width: phase === "done" ? `${display}%` : "0%" }}
        />
      </div>

      {/* meta row */}
      <div className="mt-4 flex items-center justify-between gap-2 text-[10px]">
        <span className="min-w-0 truncate text-zinc-400">
          {phase === "done" ? profile.evidence : profile.signals}
        </span>
        <span className="flex shrink-0 items-center gap-1 font-medium text-volt">
          Explainable <Check className="h-3 w-3" />
        </span>
      </div>

      {/* suggested terms (appears after assessment) */}
      {phase === "done" && (
        <p className="mt-2 rounded-xl bg-volt/10 px-3 py-2 text-[11px] text-volt-soft">
          What we found → {profile.terms}
        </p>
      )}

      <button
        onClick={run}
        disabled={phase === "analyzing"}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-volt py-3 text-sm font-bold text-[#101502] transition hover:bg-volt-soft disabled:opacity-70"
      >
        {phase === "done" ? "Re-evaluate Basket" : "Assess Basket & Arithmetic"}
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Left stat card                                                     */
/* ------------------------------------------------------------------ */

function NetworkStatCard() {
  const avatars = [
    { i: "BK", g: "from-orange-400 to-rose-500" },
    { i: "FR", g: "from-sky-400 to-teal-400" },
    { i: "SH", g: "from-violet-400 to-fuchsia-500" },
    { i: "IN", g: "from-amber-300 to-orange-500" },
  ];
  return (
    <div className="w-full max-w-[300px] rounded-3xl border border-white/10 bg-[#1b1e24]/90 p-5 shadow-2xl shadow-black/60 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium tracking-[0.14em] text-zinc-400">
          TESTS PASSING
        </p>
        <p className="flex items-center gap-1.5 text-[11px] font-semibold text-volt">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping-soft rounded-full bg-volt" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-volt" />
          </span>
          Live
        </p>
      </div>
      <p className="mt-2 text-4xl font-extrabold tracking-tight text-white">
        <CountUp to={532} duration={2.2} />
      </p>
      <p className="mt-1 text-xs text-zinc-400">
        Across 35 files · zero look-ahead verified
      </p>
      <div className="mt-4 flex items-center">
        <div className="flex -space-x-2.5">
          {avatars.map((a) => (
            <span
              key={a.i}
              className={`flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br ${a.g} text-[10px] font-bold text-white ring-2 ring-[#1b1e24]`}
            >
              {a.i}
            </span>
          ))}
        </div>
        <span className="ml-2 rounded-full bg-volt px-2.5 py-1 text-[11px] font-bold text-[#101502]">
          EN + हिन्दी
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Trusted-by logos                                                   */
/* ------------------------------------------------------------------ */

function TrustedRow() {
  return (
    <div className="relative z-10 mx-auto mt-7 w-full max-w-6xl px-6 pb-4 xl:mt-8">
      <p className="text-center text-[11px] font-semibold tracking-[0.3em] text-zinc-500">
        RUNS ENTIRELY ON YOUR MACHINE — NO CLOUD, NO BROKER, NO GUESSWORK
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 text-zinc-500">
        <span className="text-lg font-extrabold lowercase tracking-tight transition hover:text-zinc-300">
          fastapi
        </span>
        <span className="font-display text-lg font-semibold italic transition hover:text-zinc-300">
          Ollama
        </span>
        <span className="text-base font-bold tracking-[0.22em] transition hover:text-zinc-300">
          WHISPER
        </span>
        <span className="text-lg font-semibold transition hover:text-zinc-300">
          SQLite
        </span>
        <span className="flex items-center gap-1.5 text-lg font-bold transition hover:text-zinc-300">
          <span className="h-3.5 w-3.5 rounded-full border-2 border-current" />
          Pyodide
        </span>
        <span className="text-base font-semibold tracking-widest transition hover:text-zinc-300">
          1930 HELPLINE
        </span>
        <span className="text-lg font-extrabold tracking-tight transition hover:text-zinc-300">
          react
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Hero                                                               */
/* ------------------------------------------------------------------ */

export default function Hero() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <section
      id="home"
      className="relative flex min-h-[100svh] flex-col overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg, #1d1f23 0%, #16181c 45%, #0e0f12 100%)",
      }}
    >
      {/* velopay-style corner light beams */}
      <div className="absolute inset-0">
        <DotGrid />
      </div>
      <LightBeams />

      {/* globe */}
      <GlobeArt />

      <div className="relative z-10 flex flex-1 flex-col">
        {/* ---------------- Nav ---------------- */}
        <header className="relative z-30 flex items-center justify-between px-5 py-4 sm:px-8 xl:px-12 xl:py-5">
          <a href="#home" className="flex items-center gap-2.5">
            <LogoMark />
            <span className="text-xl font-extrabold tracking-tight text-white">
              jarvis
            </span>
          </a>

          <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] p-1.5 backdrop-blur-md lg:flex">
            {NAV_LINKS.map((l) => (
              <a
                key={l.label}
                href={l.href}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  l.active
                    ? "bg-white/10 font-semibold text-white"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                {l.label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-5 lg:flex">
            <a
              href="#contact"
              className="text-sm font-medium text-zinc-300 transition hover:text-white"
            >
              Docs
            </a>
            <a
              href="/index.html#/"
              className="group flex items-center gap-2 rounded-full bg-volt px-5 py-2.5 text-sm font-bold text-[#101502] transition hover:bg-volt-soft"
            >
              Run It Locally
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </a>
          </div>

          {/* mobile hamburger */}
          <button
            className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white lg:hidden"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
          >
            <div className="space-y-1.5">
              <span
                className={`block h-0.5 w-5 bg-current transition ${mobileOpen ? "translate-y-2 rotate-45" : ""}`}
              />
              <span
                className={`block h-0.5 w-5 bg-current transition ${mobileOpen ? "opacity-0" : ""}`}
              />
              <span
                className={`block h-0.5 w-5 bg-current transition ${mobileOpen ? "-translate-y-2 -rotate-45" : ""}`}
              />
            </div>
          </button>

          {mobileOpen && (
            <div className="absolute right-4 top-[72px] z-40 w-64 rounded-3xl border border-white/10 bg-[#1d2026]/95 p-3 shadow-2xl shadow-black/70 backdrop-blur-xl lg:hidden">
              {NAV_LINKS.map((l) => (
                <a
                  key={l.label}
                  href={l.href}
                  onClick={() => setMobileOpen(false)}
                  className={`block rounded-2xl px-4 py-3 text-sm transition ${
                    l.active
                      ? "bg-white/10 font-semibold text-white"
                      : "text-zinc-400 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  {l.label}
                </a>
              ))}
              <a
                href="/index.html#/"
                onClick={() => setMobileOpen(false)}
                className="mt-2 flex items-center justify-center gap-2 rounded-2xl bg-volt px-4 py-3 text-sm font-bold text-[#101502]"
              >
                Run It Locally <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          )}
        </header>

        {/* ---------------- Center content ---------------- */}
        <div className="relative z-10 flex grow flex-col items-center justify-center px-5 pb-2 pt-6 text-center sm:px-8 xl:pt-8">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 backdrop-blur-md"
          >
            <ShieldCheck className="h-4 w-4 text-volt" />
            <ShinyText
              text="100% local · Bilingual (EN + हिन्दी) · Money, plainly"
              className="text-xs font-medium text-zinc-300/85"
              speed={5}
            />
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            className="mt-3 text-[clamp(3.4rem,12vw,9rem)] font-black leading-[0.88] tracking-[-0.03em] text-white"
          >
            JARVIS
            <span className="bg-gradient-to-b from-volt-soft to-volt-deep bg-clip-text text-transparent">
              OS
            </span>
          </motion.h1>

          <div className="mt-4 max-w-xl">
            <BlurText
              text="A free, local, bilingual money guide and scam shield, built around the people who need it most and organised so each audience gets only what it needs. Every number computed by code — never guessed by an AI."
              className="text-base text-zinc-400 sm:text-lg"
              delay={28}
            />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.24 }}
            className="mt-6 flex flex-wrap items-center justify-center gap-3"
          >
            <a
              href="/index.html#/setup"
              className="group flex items-center gap-2 rounded-full bg-volt px-7 py-3.5 text-sm font-bold text-[#101502] transition hover:bg-volt-soft"
            >
              Explore 5 Baskets
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </a>
            <a
              href="/index.html#/"
              className="flex items-center gap-2.5 rounded-full border border-white/15 bg-white/[0.04] px-6 py-3.5 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-white/10"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/10">
                <Play className="ml-0.5 h-3 w-3 fill-white" />
              </span>
              See how it works
            </a>
          </motion.div>
        </div>

        {/* ---------------- Floating cards ---------------- */}
        <div className="relative z-10 mt-8 flex flex-1 flex-col items-center justify-center gap-6 px-5 sm:px-8 xl:mt-4 xl:flex-row xl:items-center xl:justify-between xl:gap-0">
          <motion.div
            initial={{ opacity: 0, x: -32 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.35 }}
            className="animate-floaty xl:ml-[3%]"
          >
            <NetworkStatCard />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 32 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.35 }}
            className="animate-floaty-slow xl:mr-[3%]"
          >
            <TrustCheckWidget />
          </motion.div>
        </div>

        {/* ---------------- Trusted logos ---------------- */}
        <TrustedRow />
      </div>
    </section>
  );
}

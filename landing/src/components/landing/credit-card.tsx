/* ------------------------------------------------------------------ */
/*  Premium black metal credit card — modelled on the reference art:  */
/*  deep gloss, warm wave reflections on the surface, embossed        */
/*  digits, gold chip, 3D perspective tilt and a travelling sheen.    */
/* ------------------------------------------------------------------ */

export default function CreditCardArt() {
  return (
    <div
      className="relative w-[240px] select-none sm:w-[300px] md:w-[340px]"
      style={{ perspective: "1200px" }}
    >
      {/* green pool of light beneath the card */}
      <div
        aria-hidden="true"
        className="absolute -inset-x-8 -bottom-12 h-28 rounded-[50%] bg-volt/25 blur-2xl"
      />

      <div
        className="relative"
        style={{
          transform: "rotateX(16deg) rotateZ(-3.5deg)",
          transformStyle: "preserve-3d",
        }}
      >
        <div className="relative aspect-[1.62/1] overflow-hidden rounded-[18px] border border-white/10 shadow-[0_60px_100px_-32px_rgba(0,0,0,0.92),0_24px_50px_-20px_rgba(184,241,77,0.28),inset_0_1px_0_rgba(255,255,255,0.16),inset_0_-1px_0_rgba(255,255,255,0.04)] sm:rounded-[22px]">
          {/* deep metal base */}
          <div className="absolute inset-0 bg-[linear-gradient(150deg,#2e2e33_0%,#1a1a1e_34%,#0b0b0d_66%,#060607_100%)]" />

          {/* green silk-wave reflections crawling on the surface */}
          <div className="absolute inset-0 mix-blend-screen bg-[radial-gradient(130%_105%_at_82%_118%,rgba(184,241,77,0.4),rgba(184,241,77,0.1)_46%,transparent_66%),radial-gradient(85%_65%_at_8%_125%,rgba(215,255,138,0.2),transparent_56%),radial-gradient(60%_45%_at_45%_-12%,rgba(230,255,200,0.12),transparent_60%)]" />

          {/* diagonal gloss */}
          <div className="absolute inset-0 bg-[linear-gradient(115deg,rgba(255,255,255,0.17)_0%,rgba(255,255,255,0.035)_24%,transparent_42%,transparent_74%,rgba(255,255,255,0.055)_100%)]" />

          {/* travelling light sweep */}
          <div className="card-sheen pointer-events-none absolute inset-y-0 left-0 w-1/2 bg-[linear-gradient(100deg,transparent_0%,rgba(255,255,255,0.11)_45%,rgba(255,255,255,0.16)_50%,rgba(255,255,255,0.11)_55%,transparent_100%)]" />

          {/* crisp top rim */}
          <div className="absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-white/55 to-transparent" />

          {/* ---------------- card face ---------------- */}
          <div className="relative flex h-full flex-col justify-between p-4 sm:p-5">
            {/* top row: brand + contactless */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                {/* shield mark */}
                <svg
                  viewBox="0 0 40 40"
                  className="h-5 w-5 drop-shadow-[0_1px_2px_rgba(0,0,0,0.7)] sm:h-6 sm:w-6"
                  aria-hidden="true"
                >
                  <path
                    d="M20 2 36 10v10c0 9.2-6.6 15.6-16 18C10.6 35.6 4 29.2 4 20V10L20 2Z"
                    fill="#b8f14d"
                  />
                  <path
                    d="M20 8.5 29.5 13v7c0 5.9-4.1 10.1-9.5 11.9C14.1 30.1 10 25.9 10 20v-7L20 8.5Z"
                    fill="#0a0a0c"
                  />
                  <circle cx="20" cy="19.5" r="4" fill="#b8f14d" />
                </svg>
                <span className="text-[11px] font-extrabold tracking-tight text-zinc-200 [text-shadow:0_1px_1px_rgba(0,0,0,0.8)] sm:text-[13px]">
                  jarvis
                </span>
              </div>
              {/* contactless */}
              <svg
                viewBox="0 0 24 24"
                className="mt-0.5 h-4 w-4 text-zinc-400 sm:h-[18px] sm:w-[18px]"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M6 8.5a8 8 0 0 1 0 7" />
                <path d="M9.5 6.5a11 11 0 0 1 0 11" />
                <path d="M13 4.5a14.5 14.5 0 0 1 0 15" />
              </svg>
            </div>

            {/* middle row: metallic gold chip */}
            <div className="h-8 w-11 rounded-md bg-[linear-gradient(135deg,#f4cd7a_0%,#dfa63e_38%,#a9701c_78%,#8a5a12_100%)] shadow-[inset_0_1px_1px_rgba(255,255,255,0.55),inset_0_-2px_3px_rgba(0,0,0,0.5),0_1px_2px_rgba(0,0,0,0.6)] sm:h-9 sm:w-12">
              <div className="mx-[6px] mt-[8px] h-px rounded bg-black/35" />
              <div className="mx-[6px] mt-[5px] h-px w-[22px] rounded bg-black/35" />
              <div className="mx-[6px] mt-[5px] h-px rounded bg-black/35" />
            </div>

            {/* bottom block: embossed number + holder */}
            <div>
              <p className="whitespace-nowrap bg-gradient-to-b from-zinc-100 via-zinc-300 to-zinc-500 bg-clip-text font-mono text-[15px] font-bold tracking-[0.14em] text-transparent [text-shadow:0_2px_2px_rgba(0,0,0,0.65)] sm:text-[19px] sm:tracking-[0.17em]">
                4018&nbsp;0086&nbsp;3357&nbsp;0008
              </p>
              <div className="mt-2.5 flex items-end justify-between sm:mt-3">
                <div>
                  <p className="text-[6.5px] font-semibold tracking-[0.28em] text-zinc-500 sm:text-[8px]">
                    SCOPE
                  </p>
                  <p className="mt-0.5 text-[9.5px] font-bold tracking-[0.16em] text-zinc-200 [text-shadow:0_1px_1px_rgba(0,0,0,0.8)] sm:text-[11px]">
                    MONEY, PLAINLY
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[6.5px] font-semibold tracking-[0.28em] text-zinc-500 sm:text-[8px]">
                    AUTOMATED TESTS
                  </p>
                  <p className="mt-0.5 text-[9.5px] font-black tracking-[0.16em] text-volt-soft [text-shadow:0_0_10px_rgba(184,241,77,0.45)] sm:text-[11px]">
                    532 / 532
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* faint hologram disc, bottom right */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -bottom-4 -right-4 h-16 w-16 rounded-full bg-[conic-gradient(from_120deg,rgba(255,255,255,0.12),rgba(184,241,77,0.16),rgba(255,255,255,0.05),rgba(215,255,138,0.12),rgba(255,255,255,0.12))] opacity-60 blur-[2px]"
          />
        </div>
      </div>
    </div>
  );
}

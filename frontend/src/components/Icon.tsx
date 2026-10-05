import type { SVGProps } from "react";

// One drawn icon set, one stroke weight (1.6 at 24px), so nothing in the product is a stand-in emoji.
const P: Record<string, string> = {
  home: "M4 11.5 12 5l8 6.5V19a1 1 0 0 1-1 1h-4v-5h-6v5H5a1 1 0 0 1-1-1z",
  portfolio: "M4 19V9m5 10V5m5 14v-8m5 8V8",
  protect: "M12 3.5 5 6v5.5c0 4.2 2.8 7.2 7 9 4.2-1.8 7-4.8 7-9V6zM9 12l2.2 2.2L15.5 10",
  rural: "M12 20v-9m0 0c0-3.2-2.2-5.2-5.5-5.5C6.2 8.7 8.3 11 12 11Zm0 3c0-3 2-4.8 5-5.2.2 3-1.8 5.2-5 5.2Z",
  whatsapp: "M5 19.5 6.2 16A7.5 7.5 0 1 1 9 18.8zM9.3 9.2c.3 2.6 2.4 4.7 5 5l1-1.3-1.6-.8-.8.7c-.9-.4-1.6-1.1-2-2l.7-.8-.8-1.6z",
  learn: "M4 6.5c2.6-.9 5.2-.9 8 .8 2.8-1.7 5.4-1.7 8-.8V18c-2.6-.9-5.2-.9-8 .8-2.8-1.7-5.4-1.7-8-.8zM12 7.3v11.5",
  practice: "M12 4v2m0 12v2M4 12h2m12 0h2M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z",
  govern: "M12 4v15M6 19h12M5 8h14M5 8l-2.5 6a3 3 0 0 0 5 0zm14 0 2.5 6a3 3 0 0 1-5 0z",
  research: "M10.5 17a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13Zm5-1.5L20 20",
  assistant: "M12 4l1.8 4.7L18.5 10l-4.7 1.3L12 16l-1.8-4.7L5.5 10l4.7-1.3zM18 16l.7 1.8L20.5 18.5l-1.8.7L18 21l-.7-1.8-1.8-.7 1.8-.7z",
  loan: "M12 4v16M8.5 8c0-1.4 1.6-2.3 3.5-2.3s3.5.9 3.5 2.3-1.6 2.1-3.5 2.4-3.5 1-3.5 2.4 1.6 2.3 3.5 2.3 3.5-.9 3.5-2.3",
  offer: "M10.5 17a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13Zm5-1.5L20 20M8.5 10.5l1.5 1.5 2.5-3",
  schemes: "M3.5 9 12 4l8.5 5M5.5 10v7m4-7v7m5-7v7m4-7v7M3.5 19.5h17",
  docs: "M7 3.5h7l4 4V20H7zM14 3.5V8h4M9.5 12.5h5m-5 3h5",
  income: "M4 18c2-5 4-6 6-6s3 4 5 4 3-6 5-9M4 21h16",
  policy: "M12 4a8 8 0 0 0-8 8h16a8 8 0 0 0-8-8Zm0 8v6.5a1.8 1.8 0 0 0 3.6 0",
  upi: "M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h2v2h-2zm4 0h2v2h-2zm-4 4h2v2h-2zm4 0h2v2h-2z",
  dbt: "M5 6.5h5m4 0h5M5 12h8m4 0h2M5 17.5h2m4 0h8M10 4v5m4 5v5m4-7v4",
  hold: "M4.5 8 12 4l7.5 4v8L12 20l-7.5-4zM4.5 8 12 12l7.5-4M12 12v8",
  saving: "M5 13c0-3.3 3-6 7-6 .9 0 1.7.1 2.4.4L17 6.5v2.6c1.2 1 2 2.4 2 3.9v2.5h-2.4L16 17.5h-2.2l-.4-1.1h-2.8l-.4 1.1H8.2L7.5 15C5.9 14.7 5 14 5 13Zm10-1.2h.01",
  group: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7 1a2.5 2.5 0 1 0 0-5M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5m1-4.5c2.5 0 4.5 1.5 4.5 4.5",
  credit: "M4 16a8 8 0 1 1 16 0M12 16l3.5-5M7 16h.01M17 16h.01M12 9v.01",
  check: "M5 12.5 10 17.5 19 7",
  warn: "M12 4 3.5 19h17zM12 10v4.5m0 2.7h.01",
  speaker: "M4 10v4h3.5L12 18V6L7.5 10zM15.5 9a4.2 4.2 0 0 1 0 6m2.3-8.3a7.5 7.5 0 0 1 0 10.6",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  close: "M6 6l12 12M18 6 6 18",
  download: "M12 4v11m-4-4 4 4 4-4M5 19h14",
  mic: "M12 15a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Zm-6-3a6 6 0 0 0 12 0M12 18v3",
};

export type IconName = keyof typeof P;

export function Icon({ name, size = 20, ...rest }: { name: IconName | string; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable="false" {...rest}>
      <path d={P[name] ?? P.assistant} />
    </svg>
  );
}

/** The brand mark: a rupee-like stroke inside an open ring. */
export function Mark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <defs><linearGradient id="mk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#ffd37a" /><stop offset="1" stopColor="#e9a42c" /></linearGradient></defs>
      <rect x="1.5" y="1.5" width="29" height="29" rx="9" fill="#17140c" stroke="url(#mk)" strokeWidth="1.4" />
      <path d="M10 10.5h12M10 15h12M13 10.5c4.5 0 6.5 1.8 6.5 4.2S17 19 13 19h-.5l6.5 5" fill="none" stroke="url(#mk)" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

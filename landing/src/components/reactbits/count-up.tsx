"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useInView } from "framer-motion";

type CountUpProps = {
  to: number;
  from?: number;
  duration?: number;
  className?: string;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  separator?: string;
};

/**
 * ReactBits-style CountUp — animates a number from `from` to `to` the first
 * time it scrolls into view. Supports decimals, prefix/suffix and separators.
 */
export default function CountUp({
  to,
  from = 0,
  duration = 2,
  className = "",
  decimals = 0,
  prefix = "",
  suffix = "",
  separator = ",",
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [value, setValue] = useState(from);

  useEffect(() => {
    if (!inView) return;
    const controls = animate(from, to, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [inView, from, to, duration]);

  const formatted = value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <span ref={ref} className={className}>
      {prefix}
      {formatted.replace(/,/g, separator)}
      {suffix}
    </span>
  );
}

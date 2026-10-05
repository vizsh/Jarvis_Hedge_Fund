"use client";

import { motion } from "framer-motion";

type BlurTextProps = {
  text: string;
  className?: string;
  delay?: number;
  animateBy?: "words" | "chars";
  direction?: "top" | "bottom";
};

/**
 * ReactBits-style BlurText — staggers words (or characters) in from a blur
 * as the text enters the viewport.
 */
export default function BlurText({
  text,
  className = "",
  delay = 90,
  animateBy = "words",
  direction = "top",
}: BlurTextProps) {
  const elements =
    animateBy === "words" ? text.split(" ") : Array.from(text);
  const y0 = direction === "top" ? -10 : 10;

  return (
    <span className={className} aria-label={text} role="text">
      {elements.map((el, i) => (
        <motion.span
          key={`${el}-${i}`}
          initial={{ filter: "blur(10px)", opacity: 0, y: y0 }}
          whileInView={{ filter: "blur(0px)", opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{
            duration: 0.45,
            delay: (i * delay) / 1000,
            ease: "easeOut",
          }}
          className="inline-block will-change-[filter,transform]"
        >
          {el}
          {animateBy === "words" && i < elements.length - 1 ? "\u00A0" : null}
        </motion.span>
      ))}
    </span>
  );
}

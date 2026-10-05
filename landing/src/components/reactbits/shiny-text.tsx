type ShinyTextProps = {
  text: string;
  className?: string;
  speed?: number;
  disabled?: boolean;
};

/**
 * ReactBits-style ShinyText — a text shimmer that sweeps across the label.
 * Base color comes from the text color utility passed via className.
 */
export default function ShinyText({
  text,
  className = "",
  speed = 4,
  disabled = false,
}: ShinyTextProps) {
  return (
    <span
      className={`shiny-text ${disabled ? "shiny-text-disabled" : ""} ${className}`}
      style={{ animationDuration: `${speed}s` }}
    >
      {text}
    </span>
  );
}

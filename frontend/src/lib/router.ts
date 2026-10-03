// Tiny hash router. Hash routes need no server rewrite rules and survive a refresh, which
// is all this app needs; a routing library would be more machinery than the problem.
import { useEffect, useState } from "react";

export const ROUTES = [
  { path: "/", label: "Home" },
  { path: "/portfolio", label: "Portfolio" },
  { path: "/protect", label: "Protect" },
  { path: "/rural", label: "Rural" },
  { path: "/learn", label: "Learn" },
  { path: "/practice", label: "Practice" },
  { path: "/govern", label: "Govern" },
  { path: "/research", label: "Research" },
  { path: "/assistant", label: "Assistant" },
] as const;

const read = () => (location.hash.replace(/^#/, "") || "/").split("?")[0];

export function useRoute(): string {
  const [route, setRoute] = useState(read());
  useEffect(() => {
    const on = () => { setRoute(read()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function go(path: string): void { location.hash = "#" + path; }

export const HI_LABEL: Record<string, string> = {
  Home: "होम", Portfolio: "पोर्टफोलियो", Protect: "सुरक्षा", Rural: "ग्रामीण", Learn: "सीखें", Practice: "अभ्यास",
  Govern: "नियम", Research: "शोध", Assistant: "सहायक",
};

/** Query parameters after the route in the hash, e.g. #/practice?a=largecap_a&b=bluechip_b */
export function hashParams(): URLSearchParams {
  return new URLSearchParams(location.hash.split("?")[1] ?? "");
}

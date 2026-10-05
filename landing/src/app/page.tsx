import Hero from "@/components/landing/hero";
import Problem from "@/components/landing/problem";
import Pillars from "@/components/landing/pillars";
import Explainable from "@/components/landing/explainable";
import HowItWorks from "@/components/landing/how-it-works";
import SiteFooter from "@/components/landing/site-footer";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-[#060607]">
      <Hero />
      <Problem />
      <Pillars />
      <Explainable />
      <HowItWorks />
      <SiteFooter />
    </main>
  );
}

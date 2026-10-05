import type { Metadata } from "next";
import { Inter, Space_Grotesk, Caveat } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

const grotesk = Space_Grotesk({
  variable: "--font-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const caveat = Caveat({
  variable: "--font-caveat",
  subsets: ["latin"],
  weight: ["500", "600"],
});

export const metadata: Metadata = {
  title: "JARVIS — money, plainly | Free, Local Money Guide & Scam Shield",
  description:
    "A free, local, bilingual money guide and scam shield, built around the people who need it most — scam protection, loan costs, government benefits, investing explained, and an honest record of decisions.",
  keywords: [
    "JARVIS money plainly",
    "scam protection",
    "1930 helpline recovery",
    "moneylender loan calculator",
    "rural finance tools",
    "DBT government schemes",
    "mutual fund overlap",
    "local AI assistant",
  ],
  icons: {
    icon: "/logo.svg",
  },
  openGraph: {
    title: "JARVIS — money, plainly | Free, Local Money Guide & Scam Shield",
    description:
      "Protect, explain, and stay honest — every number computed by code you can read, never guessed by an AI.",
    siteName: "JARVIS",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${grotesk.variable} ${caveat.variable} antialiased bg-background text-foreground font-sans`}
      >
        {children}
        <Toaster />
      </body>
    </html>
  );
}

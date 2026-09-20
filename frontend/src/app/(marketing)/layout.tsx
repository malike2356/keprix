import type { Metadata } from "next";
import Box from "@mui/material/Box";
import { DM_Sans, Fraunces, JetBrains_Mono } from "next/font/google";
import JsonLd from "@/components/marketing/JsonLd";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";

const dmSans = DM_Sans({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
  variable: "--font-mkt-sans",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  display: "swap",
  weight: ["500", "600", "700"],
  variable: "--font-mkt-display",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500"],
  variable: "--font-mkt-mono",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://keprixai.com"),
  title: {
    template: "%s | Keprix",
    default: "Keprix - Self-hosted agent OS",
  },
  description:
    "Keprix is a self-hosted agent OS: Channel Shield, Soft Wall approvals, CRM, memory, and reviewable self-coding. MIT licensed.",
  openGraph: {
    type: "website",
    siteName: "Keprix",
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box
      className={`${dmSans.variable} ${fraunces.variable} ${jetbrains.variable}`}
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        fontFamily: 'var(--font-mkt-sans), "DM Sans", sans-serif',
        letterSpacing: "-0.01em",
      }}
    >
      <JsonLd />
      <Navbar />
      <Box component="main" sx={{ flex: 1, width: "100%", overflowX: "hidden" }}>
        {children}
      </Box>
      <Footer />
    </Box>
  );
}

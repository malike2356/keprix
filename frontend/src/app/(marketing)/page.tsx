import type { Metadata } from "next";
import { Hero } from "@/components/marketing/Hero";
import { InstallSection } from "@/components/marketing/InstallSection";
import { DeferredMarketingSections } from "@/components/marketing/DeferredMarketingSections";

export const metadata: Metadata = {
  title: "Keprix - Self-hosted agent OS",
  description:
    "Self-hosted agent OS with Agent OS, Channel Shield, Agentic CRM, Universal Sidecar, Soft Wall, memory, and reviewable self-coding. MIT licensed.",
  openGraph: {
    title: "Keprix - Self-hosted agent OS",
    description:
      "Propose tools, protect channels, run CRM, embed via sidecar. Keprix tests changes and waits for your approval.",
  },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <InstallSection />
      <DeferredMarketingSections />
    </>
  );
}

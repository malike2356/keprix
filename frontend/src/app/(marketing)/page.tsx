import type { Metadata } from "next";
import { Hero } from "@/components/marketing/Hero";
import { InstallSection } from "@/components/marketing/InstallSection";
import { DeferredMarketingSections } from "@/components/marketing/DeferredMarketingSections";
import { MarketingSection } from "@/components/marketing/MarketingSection";

export const metadata: Metadata = {
  title: "Keprix - Self-hosted agent OS (open source)",
  description:
    "Open-source, self-hosted agent OS for research and building: Channel Shield, Soft Wall, memory, and reviewable self-coding with human approval. MIT licensed.",
  openGraph: {
    title: "Keprix - Self-hosted agent OS (open source)",
    description:
      "Propose tools, protect channels, keep memory local. Keprix tests changes and waits for your approval. MIT licensed.",
  },
};

export default function HomePage() {
  return (
    <>
      {/* Hero uses default (light) stripe; Install is alt (dark) so the page starts dark-light. */}
      <Hero />
      <MarketingSection tone="dark">
        <InstallSection />
      </MarketingSection>
      <DeferredMarketingSections />
    </>
  );
}

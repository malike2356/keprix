import type { Metadata } from "next";
import { Hero } from "@/components/marketing/Hero";
import { MetricsBar } from "@/components/marketing/MetricsBar";
import { FeaturesGrid } from "@/components/marketing/FeaturesGrid";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { Integrations } from "@/components/marketing/Integrations";
import { OpenSourceBand } from "@/components/marketing/OpenSourceBand";
import { FAQ } from "@/components/marketing/FAQ";
import { CTABand } from "@/components/marketing/CTABand";
import { ProductComparison } from "@/components/marketing/ProductComparison";
import { MarketingSection } from "@/components/marketing/MarketingSection";

export const metadata: Metadata = {
  title: "Keprix - Self-hosted agent OS with a Mutation engine",
  description:
    "Self-hosted, MIT-licensed AI agent runtime. Synthesise sandboxed Python tools on demand with approval, or run repo-scale changes in the self-coding agent workspace.",
  openGraph: {
    title: "Keprix - Self-hosted agent OS with a Mutation engine",
    description:
      "Self-hosted agent runtime. Mutation Engine for on-demand tools. Self-coding agent for isolated repo work. Approve before anything installs.",
  },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <MarketingSection tone="light">
        <MetricsBar />
      </MarketingSection>
      <MarketingSection tone="dark" id="features">
        <FeaturesGrid />
      </MarketingSection>
      <MarketingSection tone="light" id="how-it-works">
        <HowItWorks />
      </MarketingSection>
      <MarketingSection tone="dark">
        <Integrations />
      </MarketingSection>
      <MarketingSection tone="light">
        <OpenSourceBand />
      </MarketingSection>
      <MarketingSection tone="dark" id="compare">
        <ProductComparison />
      </MarketingSection>
      <MarketingSection tone="light">
        <FAQ />
      </MarketingSection>
      <MarketingSection tone="dark">
        <CTABand />
      </MarketingSection>
    </>
  );
}

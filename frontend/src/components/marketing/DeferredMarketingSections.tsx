"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { MarketingSection } from "@/components/marketing/MarketingSection";

const MetricsBar = dynamic(() => import("@/components/marketing/MetricsBar").then((mod) => mod.MetricsBar), {
  ssr: false,
});
const FeaturesGrid = dynamic(() => import("@/components/marketing/FeaturesGrid").then((mod) => mod.FeaturesGrid), {
  ssr: false,
});
const MutationGovernanceBand = dynamic(
  () => import("@/components/marketing/MutationGovernanceBand").then((mod) => mod.MutationGovernanceBand),
  { ssr: false },
);
const HowItWorks = dynamic(() => import("@/components/marketing/HowItWorks").then((mod) => mod.HowItWorks), {
  ssr: false,
});
const Integrations = dynamic(() => import("@/components/marketing/Integrations").then((mod) => mod.Integrations), {
  ssr: false,
});
const OpenSourceBand = dynamic(() => import("@/components/marketing/OpenSourceBand").then((mod) => mod.OpenSourceBand), {
  ssr: false,
});
const ProductComparison = dynamic(
  () => import("@/components/marketing/ProductComparison").then((mod) => mod.ProductComparison),
  { ssr: false },
);
const FAQ = dynamic(() => import("@/components/marketing/FAQ").then((mod) => mod.FAQ), {
  ssr: false,
});
const CTABand = dynamic(() => import("@/components/marketing/CTABand").then((mod) => mod.CTABand), {
  ssr: false,
});

function scheduleAfterIdle(callback: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  if (typeof window.requestIdleCallback === "function") {
    const id = window.requestIdleCallback(callback, { timeout: 1200 });
    return () => window.cancelIdleCallback(id);
  }
  const id = window.setTimeout(callback, 500);
  return () => window.clearTimeout(id);
}

export function DeferredMarketingSections() {
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => scheduleAfterIdle(() => setReady(true)), []);

  if (!ready) {
    return <MarketingSection tone="light" sx={{ minHeight: 160 }} />;
  }

  return (
    <>
      <MarketingSection tone="light">
        <MetricsBar />
      </MarketingSection>
      <MarketingSection tone="dark" id="features">
        <FeaturesGrid />
      </MarketingSection>
      <MarketingSection tone="light">
        <MutationGovernanceBand />
      </MarketingSection>
      <MarketingSection tone="light" id="how-it-works">
        <HowItWorks />
      </MarketingSection>
      <MarketingSection tone="dark" id="integrations">
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

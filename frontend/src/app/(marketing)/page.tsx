import type { Metadata } from "next";
import { Hero } from "@/components/marketing/Hero";
import { DeferredMarketingSections } from "@/components/marketing/DeferredMarketingSections";

export const metadata: Metadata = {
  title: "Keprix - The self-mutating agent OS",
  description:
    "Self-hosted agent OS with Agent OS, Channel Shield, Agentic CRM, Universal Sidecar, Soft Wall, memory, and reviewable self-coding. MIT licensed.",
  openGraph: {
    title: "Keprix - The self-mutating agent OS",
    description:
      "Create tools on demand, protect inbound channels, run CRM with Soft Wall, and embed via Universal Sidecar. Always with operator approval.",
  },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <DeferredMarketingSections />
    </>
  );
}

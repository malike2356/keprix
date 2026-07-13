import type { Metadata } from "next";
import { Hero } from "@/components/marketing/Hero";
import { DeferredMarketingSections } from "@/components/marketing/DeferredMarketingSections";

export const metadata: Metadata = {
  title: "Keprix - The self-mutating agent OS",
  description:
    "Keprix is the self-hosted, self-mutating agent OS that creates the tools it lacks, tests changes, shows risk, and waits for approval.",
  openGraph: {
    title: "Keprix - The self-mutating agent OS",
    description:
      "Keprix evolves by proposing tools, workflows, and code changes, then waiting for operator approval before upgrading itself.",
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

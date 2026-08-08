import type { Metadata } from "next";
import { FeaturesCatalogView } from "@/components/marketing/FeaturesCatalogView";

export const metadata: Metadata = {
  title: "Features and capabilities",
  description:
    "Full catalog of Keprix capabilities: Agent OS, Channel Shield, Agentic CRM, Universal Sidecar, Soft Wall, memory, vault, and more.",
};

export default function FeaturesPage() {
  return <FeaturesCatalogView />;
}

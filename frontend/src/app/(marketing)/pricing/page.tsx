import type { Metadata } from "next";
import { PricingView } from "@/components/marketing/PricingView";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Keprix is free and open source. MIT license. No seat limits, no paywalls.",
};

export default function PricingPage() {
  return <PricingView />;
}

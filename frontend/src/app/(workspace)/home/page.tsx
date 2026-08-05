"use client";

import dynamic from "next/dynamic";
import { SkeletonText } from "@/components/ui/loading";

const HomePageShell = dynamic(() => import("@/components/home/HomePageShell"), {
  ssr: false,
  loading: () => <SkeletonText lines={4} />,
});

export default function HomePage() {
  return <HomePageShell />;
}

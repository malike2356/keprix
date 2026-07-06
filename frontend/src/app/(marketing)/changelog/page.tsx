import type { Metadata } from "next";
import { ChangelogView } from "@/components/marketing/ChangelogView";
import { loadChangelog } from "@/lib/changelog";

export const metadata: Metadata = {
  title: "Changelog",
  description: "Release history, shipped features, and in-development changes for Keprix.",
};

/** Re-read CHANGELOG.md periodically without a full redeploy (ISR). */
export const revalidate = 300;

export default function ChangelogPage() {
  const releases = loadChangelog();
  return <ChangelogView releases={releases} />;
}

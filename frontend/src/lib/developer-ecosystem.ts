/** Sibling products by the Keprix maintainer. Canonical list: /verlox/ecosystem-links.json */

export const DEVELOPER_ECOSYSTEM_LABEL = "From the same developer";

export type DeveloperEcosystemLink = {
  label: string;
  href: string;
  title: string;
};

export const DEVELOPER_ECOSYSTEM: readonly DeveloperEcosystemLink[] = [
  { label: "Keprix", href: "https://github.com/malike2356/keprix", title: "Self-hosted AI agent OS" },
  { label: "Carina", href: "https://github.com/malike2356/carina", title: "Open-source agent platform" },
  { label: "Scout", href: "https://labyrinthscout.com", title: "Agent governance research" },
  { label: "malike2356", href: "https://github.com/malike2356", title: "Developer profile" },
] as const;

/** Sibling products by the Keprix maintainer. Canonical list: /verlox/ecosystem-links.json */

export const DEVELOPER_ECOSYSTEM_LABEL = "From the same developer";

export type DeveloperEcosystemLink = {
  label: string;
  href: string;
  title: string;
};

export const DEVELOPER_ECOSYSTEM: readonly DeveloperEcosystemLink[] = [
  { label: "Keprix", href: "https://github.com/malike2356/keprix", title: "Self-hosted AI agent OS" },
  { label: "Verlox", href: "https://verlox.uk", title: "Company & enterprise solutions" },
  { label: "malike2356", href: "https://github.com/malike2356", title: "Developer profile" },
  { label: "Aiva", href: "https://hireaiva.co.uk", title: "Managed AI workers" },
  { label: "Scout", href: "https://labyrinthscout.com", title: "Governance console" },
  { label: "Propreneur", href: "https://propreneur.uk", title: "Property investor OS" },
  { label: "TuinApp", href: "https://tuinapp.uk", title: "Workforce SaaS" },
  { label: "PropCalc", href: "https://propcalc.uk", title: "Property calculators" },
] as const;

import type { ThemeMode } from "@/theme/tokens/colors";

export type MarketingTone = "default" | "alt";

export type MarketingColors = {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  info: string;
  bgDefault: string;
  bgPaper: string;
  bgCard: string;
  textPrimary: string;
  textSecondary: string;
  divider: string;
};

/**
 * Marketing type: one serif display, one sans body, one mono.
 * Loaded in (marketing)/layout.tsx via next/font CSS variables.
 */
export const MARKETING_DISPLAY_FONT =
  'var(--font-mkt-display), "Fraunces", "Source Serif 4", Georgia, "Times New Roman", serif';

export const MARKETING_BODY_FONT =
  'var(--font-mkt-sans), "DM Sans", "Helvetica Neue", Arial, sans-serif';

export const MARKETING_MONO_FONT =
  'var(--font-mkt-mono), "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace';

export const MARKETING_EYEBROW_SX = {
  fontFamily: MARKETING_BODY_FONT,
  fontSize: "0.72rem",
  fontWeight: 600,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
} as const;

export const MARKETING_HEADING_SX = {
  fontFamily: MARKETING_DISPLAY_FONT,
  fontWeight: 600,
  letterSpacing: "-0.02em",
  lineHeight: 1.08,
} as const;

/**
 * Engineered palette: stone paper + one teal accent.
 * No purple gradients, no glow spheres, no rainbow KPI tiles.
 */
const DARK_DEFAULT: MarketingColors = {
  primary: "#2DD4BF",
  secondary: "#2DD4BF",
  success: "#34D399",
  warning: "#FBBF24",
  info: "#2DD4BF",
  bgDefault: "#0C0C0B",
  bgPaper: "#141413",
  bgCard: "#1A1A18",
  textPrimary: "rgba(250,250,249,0.92)",
  textSecondary: "rgba(250,250,249,0.58)",
  divider: "rgba(250,250,249,0.08)",
};

const DARK_ALT: MarketingColors = {
  ...DARK_DEFAULT,
  bgDefault: "#141413",
  bgPaper: "#1A1A18",
  bgCard: "#222220",
};

const LIGHT_DEFAULT: MarketingColors = {
  primary: "#0F766E",
  secondary: "#0F766E",
  success: "#047857",
  warning: "#B45309",
  info: "#0F766E",
  bgDefault: "#FAFAF9",
  bgPaper: "#FFFFFF",
  bgCard: "#F5F5F4",
  textPrimary: "#1C1917",
  textSecondary: "#57534E",
  divider: "rgba(28,25,23,0.1)",
};

const LIGHT_ALT: MarketingColors = {
  ...LIGHT_DEFAULT,
  bgDefault: "#F5F5F4",
  bgPaper: "#FFFFFF",
  bgCard: "#E7E5E4",
};

/** Resolve marketing palette from global theme mode and optional section stripe. */
export function getMarketingColors(mode: ThemeMode, tone: MarketingTone = "default"): MarketingColors {
  if (mode === "light") {
    return tone === "alt" ? LIGHT_ALT : LIGHT_DEFAULT;
  }
  return tone === "alt" ? DARK_ALT : DARK_DEFAULT;
}

/** @deprecated Prefer getMarketingColors(mode, tone). Kept for older tone="light"|"dark" call sites. */
export function resolveMarketingTone(tone: "light" | "dark" | MarketingTone): MarketingTone {
  if (tone === "light" || tone === "default") return "default";
  if (tone === "dark" || tone === "alt") return "alt";
  return "default";
}

/** Shared button shapes for the makeover: square-ish, not pills. */
export const MARKETING_BTN_RADIUS = "6px";

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

export const MARKETING_DISPLAY_FONT = '"Cormorant Garamond", Georgia, serif';

export const MARKETING_EYEBROW_SX = {
  fontSize: "0.78rem",
  fontWeight: 800,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
} as const;

export const MARKETING_HEADING_SX = {
  fontFamily: MARKETING_DISPLAY_FONT,
  fontWeight: 700,
  letterSpacing: "-0.02em",
  lineHeight: 1.04,
} as const;

const DARK_DEFAULT: MarketingColors = {
  primary: "#6c5ce7",
  secondary: "#6495ed",
  success: "#10B981",
  warning: "#F59E0B",
  info: "#6495ed",
  bgDefault: "#08080f",
  bgPaper: "#0d0d1a",
  bgCard: "#0f0f1e",
  textPrimary: "#ededf8",
  textSecondary: "#8888a8",
  divider: "rgba(255,255,255,0.07)",
};

const DARK_ALT: MarketingColors = {
  ...DARK_DEFAULT,
  bgDefault: "#0d0d1a",
  bgPaper: "#12121f",
  bgCard: "#161628",
};

const LIGHT_DEFAULT: MarketingColors = {
  primary: "#6c5ce7",
  secondary: "#4682b4",
  success: "#059669",
  warning: "#D97706",
  info: "#2563EB",
  bgDefault: "#ffffff",
  bgPaper: "#ffffff",
  bgCard: "#f8f8fc",
  textPrimary: "#18181e",
  textSecondary: "#4a4a66",
  divider: "#e2e2ec",
};

const LIGHT_ALT: MarketingColors = {
  ...LIGHT_DEFAULT,
  bgDefault: "#f5f5fa",
  bgPaper: "#ffffff",
  bgCard: "#eeeef6",
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

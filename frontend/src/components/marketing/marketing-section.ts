import type { ThemeMode } from "@/theme/tokens/colors";

export type MarketingTone = ThemeMode;

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

export function getMarketingColors(tone: MarketingTone): MarketingColors {
  if (tone === "dark") {
    return {
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
  }
  return {
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
}

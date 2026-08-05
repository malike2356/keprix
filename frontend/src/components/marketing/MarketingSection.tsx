"use client";

import Box from "@mui/material/Box";
import type { SxProps, Theme } from "@mui/material/styles";
import * as React from "react";
import {
  MARKETING_DISPLAY_FONT,
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  getMarketingColors,
  resolveMarketingTone,
  type MarketingTone,
} from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const MarketingSectionContext = React.createContext(getMarketingColors("dark"));

export function useMarketingColors() {
  return React.useContext(MarketingSectionContext);
}

export { MARKETING_DISPLAY_FONT, MARKETING_EYEBROW_SX, MARKETING_HEADING_SX } from "@/components/marketing/marketing-section";

type MarketingSectionProps = {
  /** Section stripe within the active theme. Legacy "light"|"dark" still accepted. */
  tone?: MarketingTone | "light" | "dark";
  id?: string;
  children?: React.ReactNode;
  sx?: SxProps<Theme>;
};

export function MarketingSection({ tone = "default", id, children, sx }: MarketingSectionProps) {
  const { mode } = useThemeMode();
  const stripe = resolveMarketingTone(tone);
  const colors = getMarketingColors(mode, stripe);

  return (
    <MarketingSectionContext.Provider value={colors}>
      <Box
        id={id}
        component="section"
        sx={{
          width: "100%",
          maxWidth: "100%",
          bgcolor: colors.bgDefault,
          color: colors.textPrimary,
          transition: "background-color 0.25s ease, color 0.25s ease",
          ...sx,
        }}
      >
        {children}
      </Box>
    </MarketingSectionContext.Provider>
  );
}

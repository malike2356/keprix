"use client";

import Box from "@mui/material/Box";
import type { SxProps, Theme } from "@mui/material/styles";
import * as React from "react";
import { getMarketingColors, type MarketingTone } from "@/components/marketing/marketing-section";

const MarketingSectionContext = React.createContext(getMarketingColors("dark"));

export function useMarketingColors() {
  return React.useContext(MarketingSectionContext);
}

type MarketingSectionProps = {
  tone: MarketingTone;
  id?: string;
  children: React.ReactNode;
  sx?: SxProps<Theme>;
};

export function MarketingSection({ tone, id, children, sx }: MarketingSectionProps) {
  const colors = getMarketingColors(tone);

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
          ...sx,
        }}
      >
        {children}
      </Box>
    </MarketingSectionContext.Provider>
  );
}

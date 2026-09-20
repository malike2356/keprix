"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { MARKETING_DISPLAY_FONT } from "@/components/marketing/marketing-section";

const METRICS = [
  {
    value: "1",
    label: "runtime, many surfaces",
    detail: "Web workspace, TUI, CLI, API, and mobile.",
  },
  {
    value: "100%",
    label: "self-hosted, your data",
    detail: "Your server. Your database. No shared keys.",
  },
  {
    value: "MIT",
    label: "open source license",
    detail: "Use commercially, modify freely, then self-host.",
  },
  {
    value: "~3m",
    label: "cold install on Linux",
    detail: "Curl install with Python 3.11+, then keprix --version.",
  },
] as const;

export function MetricsBar() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 6, md: 7 },
        borderTop: `1px solid ${c.divider}`,
        borderBottom: `1px solid ${c.divider}`,
      }}
    >
      <Container maxWidth="lg">
        <ScrollReveal>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr 1fr" },
              gap: { xs: 3, md: 0 },
            }}
          >
            {METRICS.map((m, i) => (
              <Box
                key={m.label}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  px: { xs: 1, md: 3 },
                  py: { xs: 1, md: 0 },
                  borderRight: {
                    xs: "none",
                    md: i < METRICS.length - 1 ? `1px solid ${c.divider}` : "none",
                  },
                }}
              >
                <Typography
                  sx={{
                    fontFamily: MARKETING_DISPLAY_FONT,
                    fontSize: { xs: "2rem", md: "2.35rem" },
                    fontWeight: 600,
                    letterSpacing: "-0.03em",
                    lineHeight: 1,
                    mb: 1,
                    color: c.textPrimary,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {m.value}
                </Typography>
                <Typography
                  sx={{
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    color: c.textPrimary,
                    mb: 0.5,
                  }}
                >
                  {m.label}
                </Typography>
                <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary, lineHeight: 1.5 }}>
                  {m.detail}
                </Typography>
              </Box>
            ))}
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}

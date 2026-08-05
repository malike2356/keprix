"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

const METRICS = [
  {
    value: "1",
    label: "runtime, many surfaces",
    detail: "Web workspace, TUI, CLI, REST API, and mobile client.",
    color: "#6c5ce7",
  },
  {
    value: "100%",
    label: "self-hosted, your data",
    detail: "Your server. Your database. No shared keys.",
    color: "#10B981",
  },
  {
    value: "MIT",
    label: "open-source license",
    detail: "Use commercially. Modify. Self-host.",
    color: "#6495ed",
  },
  {
    value: "100/100",
    label: "TUI parity target",
    detail: "Hermes behavior parity with Keprix look and extensions.",
    color: "#F59E0B",
  },
] as const;

export function MetricsBar() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 6, md: 8 },
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
                  alignItems: "center",
                  textAlign: "center",
                  px: { xs: 2, md: 4 },
                  py: { xs: 1, md: 0 },
                  borderRight: {
                    xs: "none",
                    md: i < METRICS.length - 1 ? `1px solid ${c.divider}` : "none",
                  },
                }}
              >
                <Typography
                  sx={{
                    fontSize: { xs: "2rem", md: "2.5rem" },
                    fontWeight: 800,
                    letterSpacing: "-0.04em",
                    lineHeight: 1,
                    mb: 0.75,
                    color: m.color,
                  }}
                >
                  {m.value}
                </Typography>
                <Typography
                  sx={{
                    fontSize: "0.8rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: c.textPrimary,
                    mb: 0.5,
                  }}
                >
                  {m.label}
                </Typography>
                <Typography
                  sx={{
                    fontSize: "0.78rem",
                    color: c.textSecondary,
                    lineHeight: 1.5,
                    maxWidth: 180,
                  }}
                >
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

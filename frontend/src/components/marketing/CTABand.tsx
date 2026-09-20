"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import {
  MARKETING_BTN_RADIUS,
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

export function CTABand() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";

  return (
    <Box
      sx={{
        py: { xs: 10, md: 14 },
        borderTop: `1px solid ${c.divider}`,
        bgcolor: c.bgDefault,
      }}
    >
      <Container maxWidth="md">
        <ScrollReveal>
          <Typography
            component="p"
            sx={{
              ...MARKETING_EYEBROW_SX,
              color: c.primary,
              mb: 1.5,
            }}
          >
            Get started
          </Typography>
          <Typography
            component="h2"
            sx={{
              ...MARKETING_HEADING_SX,
              fontSize: { xs: "2.1rem", md: "2.85rem" },
              mb: 2,
              color: c.textPrimary,
              maxWidth: 560,
            }}
          >
            Run the agent OS on your own iron.
          </Typography>
          <Typography
            sx={{
              color: c.textSecondary,
              mb: 4,
              fontSize: "1rem",
              lineHeight: 1.7,
              maxWidth: 440,
            }}
          >
            Agents, memory, playbooks, Channel Shield, and approvals from your infrastructure.
          </Typography>
          <Box sx={{ display: "flex", gap: 2.5, alignItems: "center", flexWrap: "wrap" }}>
            <Button
              component="a"
              href="/#install"
              onClick={(e) => {
                if (typeof window !== "undefined" && window.location.pathname === "/") {
                  const el = document.getElementById("install");
                  if (el) {
                    e.preventDefault();
                    el.scrollIntoView({ behavior: "smooth" });
                    window.history.pushState(null, "", "#install");
                  }
                }
              }}
              variant="contained"
              size="large"
              sx={{
                fontWeight: 600,
                px: 2.75,
                borderRadius: MARKETING_BTN_RADIUS,
                bgcolor: c.primary,
                color: isDark ? "#0C0C0B" : "#FAFAF9",
                boxShadow: "none",
                textTransform: "none",
                "&:hover": {
                  bgcolor: c.primary,
                  filter: "brightness(1.06)",
                  boxShadow: "none",
                },
              }}
            >
              Install Community
            </Button>
            <Button
              component="a"
              href="/docs"
              endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
              sx={{
                fontWeight: 500,
                px: 0.5,
                color: c.textSecondary,
                textTransform: "none",
                "&:hover": {
                  bgcolor: "transparent",
                  color: c.textPrimary,
                },
              }}
            >
              Read the docs
            </Button>
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}

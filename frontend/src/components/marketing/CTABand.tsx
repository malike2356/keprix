"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import Link from "next/link";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

const DottedSurfaceBackground = dynamic(
  () => import("@/components/ui/dotted-surface-background").then((mod) => mod.DottedSurfaceBackground),
  { ssr: false },
);

export function CTABand() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 14, md: 20 },
        textAlign: "center",
        position: "relative",
        overflow: "hidden",
        bgcolor: c.bgDefault,
      }}
    >
      <DottedSurfaceBackground />

      {/* Vignette */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
          pointerEvents: "none",
          background: `
            radial-gradient(ellipse at 50% 35%, ${alpha(c.primary, 0.08)} 0%, transparent 45%),
            radial-gradient(ellipse at 50% 100%, ${alpha(c.bgDefault, 0.35)} 0%, transparent 65%)
          `,
        }}
      />

      {/* Bottom glow */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          bottom: -100,
          left: "50%",
          transform: "translateX(-50%)",
          width: 900,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(ellipse at center, ${alpha(c.primary, 0.16)} 0%, transparent 70%)`,
          filter: "blur(48px)",
          pointerEvents: "none",
        }}
      />
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: -80,
          left: -80,
          width: 320,
          height: 320,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${alpha(c.secondary, 0.07)} 0%, transparent 70%)`,
          filter: "blur(40px)",
          pointerEvents: "none",
        }}
      />
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: -80,
          right: -80,
          width: 320,
          height: 320,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${alpha(c.primary, 0.08)} 0%, transparent 70%)`,
          filter: "blur(40px)",
          pointerEvents: "none",
        }}
      />

      <Container maxWidth="sm" sx={{ position: "relative", zIndex: 1 }}>
        <ScrollReveal>
          <Typography
            component="p"
            sx={{
              fontSize: "0.78rem",
              fontWeight: 700,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: c.primary,
              mb: 2,
            }}
          >
            Get started
          </Typography>
          <Typography
            component="h2"
            sx={{
              fontSize: { xs: "2.25rem", md: "3rem" },
              fontWeight: 800,
              letterSpacing: "-0.035em",
              lineHeight: 1.1,
              mb: 2.5,
              background: `linear-gradient(140deg, ${c.textPrimary} 30%, ${alpha(c.primary, 0.85)} 100%)`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Self-host your AI agent OS in under 3 minutes.
          </Typography>
          <Typography
            sx={{
              color: c.textSecondary,
              mb: 5.5,
              fontSize: "1rem",
              lineHeight: 1.75,
              maxWidth: 380,
              mx: "auto",
            }}
          >
            Self-hosted. MIT licensed. No cloud accounts required.
          </Typography>
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
            <Button
              component={Link}
              href="/auth/setup"
              variant="contained"
              size="large"
              sx={{
                fontWeight: 700,
                px: 4,
                borderRadius: "9999px",
                background: `linear-gradient(135deg, ${c.primary} 0%, ${c.secondary} 100%)`,
                boxShadow: `0 4px 28px ${alpha(c.primary, 0.45)}`,
                "&:hover": { boxShadow: `0 6px 36px ${alpha(c.primary, 0.6)}` },
              }}
            >
              Deploy free
            </Button>
            <Button
              component={Link}
              href="/docs"
              variant="outlined"
              size="large"
              sx={{
                fontWeight: 600,
                px: 4,
                borderRadius: "9999px",
                borderColor: "rgba(255,255,255,0.12)",
                color: c.textSecondary,
                "&:hover": {
                  borderColor: alpha(c.primary, 0.5),
                  color: c.textPrimary,
                  bgcolor: alpha(c.primary, 0.06),
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

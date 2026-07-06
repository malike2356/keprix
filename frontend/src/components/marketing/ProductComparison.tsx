"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { ProductComparisonTable } from "@/components/marketing/ProductComparisonTable";

export function ProductComparison() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 10, md: 14 },
        position: "relative",
        overflow: "hidden",
        bgcolor: c.bgDefault,
      }}
    >
      {/* Separator line */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "60%",
          height: 1,
          background: `linear-gradient(90deg, transparent, ${alpha(c.primary, 0.3)}, transparent)`,
        }}
      />

      <Container maxWidth="md" sx={{ position: "relative" }}>
        <ScrollReveal>
          <Box
            sx={{
              borderRadius: 3,
              border: `1px solid rgba(255,255,255,0.08)`,
              bgcolor: "rgba(10,10,22,0.55)",
              backdropFilter: "blur(20px)",
              boxShadow: `inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 32px rgba(0,0,0,0.4)`,
              p: { xs: 4, md: 6 },
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              alignItems: { xs: "flex-start", sm: "center" },
              gap: 4,
              position: "relative",
              overflow: "hidden",
              cursor: "default",
              transition: "transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.35s, box-shadow 0.35s",
              "@media (prefers-reduced-motion: no-preference)": {
                "&:hover": {
                  transform: "translateY(-6px)",
                  borderColor: alpha(c.secondary, 0.38),
                  boxShadow: `inset 0 1px 0 rgba(255,255,255,0.1), 0 20px 56px rgba(0,0,0,0.55), 0 0 0 1px ${alpha(c.secondary, 0.18)}`,
                  "& .comparison-glow": {
                    opacity: 1,
                    transform: "translateY(-50%) scale(1.12)",
                  },
                  "& .comparison-gloss": {
                    opacity: 1,
                  },
                },
              },
            }}
          >
            {/* Specular gloss */}
            <Box
              className="comparison-gloss"
              aria-hidden
              sx={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: "50%",
                background:
                  "linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%)",
                pointerEvents: "none",
                borderRadius: "12px 12px 0 0",
                opacity: 0.7,
                transition: "opacity 0.35s ease",
              }}
            />

            {/* Accent glow */}
            <Box
              className="comparison-glow"
              aria-hidden
              sx={{
                position: "absolute",
                right: -80,
                top: "50%",
                transform: "translateY(-50%)",
                width: 280,
                height: 280,
                borderRadius: "50%",
                background: `radial-gradient(circle, ${alpha(c.secondary, 0.16)} 0%, transparent 70%)`,
                filter: "blur(32px)",
                pointerEvents: "none",
                opacity: 0.55,
                transition: "opacity 0.4s ease, transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)",
              }}
            />

            <Box sx={{ flex: 1, position: "relative" }}>
              <Typography
                component="p"
                sx={{
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: c.secondary,
                  mb: 1.5,
                }}
              >
                Need more?
              </Typography>
              <Typography
                component="h2"
                sx={{
                  fontSize: { xs: "1.5rem", md: "1.85rem" },
                  fontWeight: 800,
                  letterSpacing: "-0.025em",
                  lineHeight: 1.2,
                  mb: 1.5,
                  background: `linear-gradient(140deg, ${c.textPrimary} 30%, ${alpha(c.secondary, 0.9)} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                Managed hosting, enterprise SaaS, and SOC tooling built on Keprix.
              </Typography>
              <Typography
                sx={{ color: c.textSecondary, fontSize: "0.9rem", lineHeight: 1.7, maxWidth: 460 }}
              >
                Aiva by Carina is a managed SaaS platform built on the Keprix engine. It adds white-label branding, multi-tenant SOC, SLA support, and enterprise governance. Keprix and Aiva are separate products.
              </Typography>
            </Box>

            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 1.5,
                flexShrink: 0,
                position: "relative",
              }}
            >
              <Button
                component="a"
                href="https://aiva.carina.ai"
                target="_blank"
                rel="noopener noreferrer"
                variant="contained"
                endIcon={<OpenInNewIcon sx={{ fontSize: "0.9rem !important" }} />}
                sx={{
                  fontWeight: 700,
                  px: 3.5,
                  borderRadius: "9999px",
                  whiteSpace: "nowrap",
                  background: `linear-gradient(135deg, ${c.secondary} 0%, ${c.primary} 100%)`,
                  backgroundSize: "200% 200%",
                  backgroundPosition: "0% 50%",
                  boxShadow: `0 4px 24px ${alpha(c.secondary, 0.35)}`,
                  transition:
                    "transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s, background-position 0.45s ease",
                  "& .MuiButton-endIcon": {
                    transition: "transform 0.3s cubic-bezier(0.22, 1, 0.36, 1)",
                  },
                  "@media (prefers-reduced-motion: no-preference)": {
                    "&:hover": {
                      transform: "translateY(-2px) scale(1.03)",
                      backgroundPosition: "100% 50%",
                      boxShadow: `0 10px 36px ${alpha(c.secondary, 0.55)}, 0 0 24px ${alpha(c.primary, 0.25)}`,
                      "& .MuiButton-endIcon": {
                        transform: "translate(3px, -3px)",
                      },
                    },
                    "&:active": {
                      transform: "translateY(0) scale(0.99)",
                    },
                  },
                }}
              >
                See Aiva by Carina
              </Button>
              <Typography
                sx={{
                  fontSize: "0.72rem",
                  color: alpha(c.textSecondary, 0.55),
                  textAlign: "center",
                }}
              >
                Separate product, separate pricing
              </Typography>
            </Box>
          </Box>
        </ScrollReveal>

        <ScrollReveal delay={0.08}>
          <ProductComparisonTable />
        </ScrollReveal>
      </Container>
    </Box>
  );
}

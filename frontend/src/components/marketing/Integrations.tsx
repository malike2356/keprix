"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha, keyframes } from "@mui/material/styles";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { INTEGRATION_PROVIDERS } from "@/components/marketing/integrations-data";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const scroll = keyframes`
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
`;

export function IntegrationsMarquee() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";
  const doubled = [...INTEGRATION_PROVIDERS, ...INTEGRATION_PROVIDERS];

  return (
    <Box sx={{ overflow: "hidden", position: "relative" }}>
      <Box
        sx={{
          "&::before, &::after": {
            content: '""',
            position: "absolute",
            top: 0,
            bottom: 0,
            width: 120,
            zIndex: 1,
          },
          "&::before": {
            left: 0,
            background: `linear-gradient(to right, ${c.bgDefault}, transparent)`,
          },
          "&::after": {
            right: 0,
            background: `linear-gradient(to left, ${c.bgDefault}, transparent)`,
          },
        }}
      >
        <Box
          sx={{
            display: "flex",
            gap: 3,
            width: "max-content",
            animation: `${scroll} 32s linear infinite`,
            "&:hover": { animationPlayState: "paused" },
          }}
        >
          {doubled.map((p, i) => (
            <Box
              key={`${p.name}-${i}`}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                px: 2.5,
                py: 1.25,
                border: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : c.divider}`,
                borderRadius: 5,
                bgcolor: isDark ? "rgba(12,12,22,0.6)" : c.bgCard,
                backdropFilter: isDark ? "blur(12px)" : "none",
                whiteSpace: "nowrap",
                flexShrink: 0,
                boxShadow: isDark
                  ? `inset 0 1px 0 rgba(255,255,255,0.05)`
                  : `0 1px 2px ${alpha("#000", 0.04)}`,
                transition: "border-color 0.2s, box-shadow 0.2s",
                "&:hover": {
                  borderColor: alpha(p.color, 0.4),
                  boxShadow: isDark
                    ? `0 0 16px ${alpha(p.color, 0.15)}, inset 0 1px 0 rgba(255,255,255,0.08)`
                    : `0 2px 8px ${alpha(p.color, 0.12)}`,
                },
              }}
            >
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: p.color,
                  flexShrink: 0,
                  boxShadow: `0 0 8px ${alpha(p.color, isDark ? 0.8 : 0.45)}`,
                }}
              />
              <Typography
                sx={{
                  fontSize: "0.875rem",
                  color: c.textPrimary,
                  fontWeight: 600,
                  letterSpacing: "-0.01em",
                }}
              >
                {p.name}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

export function Integrations() {
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
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "60%",
          height: 1,
          background: `linear-gradient(90deg, transparent, ${alpha(c.primary, 0.4)}, transparent)`,
        }}
      />

      <Container maxWidth="lg">
        <ScrollReveal>
          <Typography
            sx={{
              textAlign: "center",
              fontSize: "0.8rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              color: alpha(c.textSecondary, 0.6),
              mb: 6,
            }}
          >
            Works with
          </Typography>
        </ScrollReveal>
      </Container>

      <IntegrationsMarquee />
    </Box>
  );
}

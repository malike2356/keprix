"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import LinkIcon from "@mui/icons-material/Link";
import TerminalIcon from "@mui/icons-material/Terminal";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const STEPS = [
  {
    number: "01",
    icon: RocketLaunchIcon,
    title: "Deploy",
    body: "Three commands on your machine or VPS. No cloud account required.",
    detail: {
      type: "code" as const,
      lines: [
        { prefix: "$", text: "git clone github.com/malike2356/keprix" },
        { prefix: "$", text: "cd keprix && cp .env.example .env" },
        { prefix: "$", text: "docker compose -f docker/docker-compose.yml up" },
      ],
    },
  },
  {
    number: "02",
    icon: LinkIcon,
    title: "Configure",
    body: "Add providers, channels, credentials, policies, and workspace settings under your control.",
    detail: {
      type: "channels" as const,
      items: ["Models", "Memory", "Channel Shield", "MCP"],
    },
  },
  {
    number: "03",
    icon: TerminalIcon,
    title: "Operate",
    body: "Use the web workspace or Command Center TUI to run agents, inspect tools, approve changes, and monitor runtime health.",
    detail: {
      type: "conversation" as const,
      lines: [
        { role: "user", text: "/status" },
        { role: "agent", text: "Runtime healthy. 0 queued." },
        { role: "system", text: "Channel Shield: idle" },
        { role: "agent", text: "Review gateway ready." },
      ],
    },
  },
] as const;

const ROLE_COLORS_DARK: Record<string, string> = {
  user: "rgba(96,165,250,0.9)",
  agent: "rgba(108,92,231,0.9)",
  system: "rgba(251,191,36,0.9)",
};

const ROLE_COLORS_LIGHT: Record<string, string> = {
  user: "#2563EB",
  agent: "#6c5ce7",
  system: "#D97706",
};

function StepDetail({
  detail,
}: {
  detail: (typeof STEPS)[number]["detail"];
}) {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";
  const roleColors = isDark ? ROLE_COLORS_DARK : ROLE_COLORS_LIGHT;

  if (detail.type === "code") {
    return (
      <Box
        sx={{
          mt: "auto",
          p: 1.25,
          bgcolor: isDark ? "rgba(6,6,14,0.8)" : alpha(c.bgCard, 0.95),
          border: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : c.divider}`,
          borderRadius: 1.5,
          fontFamily: "monospace",
          fontSize: "0.62rem",
          lineHeight: 1.6,
        }}
      >
        {detail.lines.map((line) => (
          <Box key={line.text} sx={{ display: "flex", gap: 1.25 }}>
            <Box component="span" sx={{ color: alpha(c.primary, isDark ? 0.85 : 1), flexShrink: 0 }}>
              {line.prefix}
            </Box>
            <Box
              component="span"
              sx={{
                color: isDark ? "rgba(237,237,248,0.95)" : c.textPrimary,
                wordBreak: "break-all",
              }}
            >
              {line.text}
            </Box>
          </Box>
        ))}
      </Box>
    );
  }

  if (detail.type === "channels") {
    return (
      <Box sx={{ mt: "auto", display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {detail.items.map((item) => (
          <Box
            key={item}
            sx={{
              px: 1.1,
              py: 0.35,
              borderRadius: 4,
              fontSize: "0.65rem",
              fontWeight: 600,
              color: isDark ? "#ededf8" : c.textPrimary,
              bgcolor: isDark ? "rgba(255,255,255,0.06)" : alpha(c.primary, 0.06),
              border: `1px solid ${isDark ? "rgba(255,255,255,0.14)" : c.divider}`,
            }}
          >
            {item}
          </Box>
        ))}
      </Box>
    );
  }

  if (detail.type === "conversation") {
    return (
      <Box
        sx={{
          mt: "auto",
          p: 1.25,
          bgcolor: isDark ? "rgba(6,6,14,0.8)" : alpha(c.bgCard, 0.95),
          border: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : c.divider}`,
          borderRadius: 1.5,
          fontFamily: "monospace",
          fontSize: "0.6rem",
          lineHeight: 1.55,
        }}
      >
        {detail.lines.map((line) => (
          <Box key={`${line.role}-${line.text}`} sx={{ display: "flex", gap: 0.75, mb: 0.15 }}>
            <Box
              component="span"
              sx={{
                color: roleColors[line.role] ?? c.textSecondary,
                flexShrink: 0,
                minWidth: 34,
                textTransform: "uppercase",
                fontSize: "0.55rem",
                fontWeight: 700,
              }}
            >
              {line.role === "user" ? "you" : line.role === "agent" ? "agent" : "sys"}
            </Box>
            <Box
              component="span"
              sx={{ color: isDark ? "rgba(237,237,248,0.92)" : c.textPrimary }}
            >
              {line.text}
            </Box>
          </Box>
        ))}
      </Box>
    );
  }

  return null;
}

export function HowItWorks() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";

  return (
    <Box
      sx={{
        py: { xs: 12, md: 18 },
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle grid; kept low so it does not wash over cards */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
          opacity: 0.35,
          backgroundImage: `
            linear-gradient(${alpha(c.primary, 0.06)} 1px, transparent 1px),
            linear-gradient(90deg, ${alpha(c.primary, 0.06)} 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
          maskImage: "linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.25) 40%, transparent 85%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.25) 40%, transparent 85%)",
          pointerEvents: "none",
        }}
      />

      <Container maxWidth="lg" sx={{ position: "relative", zIndex: 1 }}>
        <ScrollReveal>
          <Box sx={{ textAlign: "center", mb: { xs: 6, md: 7 } }}>
            <Typography
              component="p"
              sx={{
                ...MARKETING_EYEBROW_SX,
                color: c.secondary,
                mb: 2,
              }}
            >
              Getting started
            </Typography>
            <Typography
              component="h2"
              sx={{
                ...MARKETING_HEADING_SX,
                fontSize: { xs: "2.2rem", md: "3rem" },
                mb: 2,
                color: c.textPrimary,
              }}
            >
              Up and running in minutes.
            </Typography>
            <Typography
              sx={{ color: c.textSecondary, maxWidth: 440, mx: "auto", fontSize: "1rem", lineHeight: 1.7 }}
            >
              Deploy locally, configure your runtime, then operate agents from the browser or terminal.
            </Typography>
          </Box>
        </ScrollReveal>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
            gap: { xs: 2, md: 2 },
            alignItems: "stretch",
          }}
        >
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <ScrollReveal key={step.number} delay={i * 0.08}>
                <Box
                  sx={{
                    height: "100%",
                    minHeight: { md: 280 },
                    p: { xs: 2, md: 2.25 },
                    borderRadius: 2,
                    bgcolor: isDark ? c.bgCard : c.bgPaper,
                    border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : c.divider}`,
                    position: "relative",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    gap: 1.5,
                    boxShadow: isDark
                      ? "0 6px 24px rgba(8,8,15,0.3), inset 0 1px 0 rgba(255,255,255,0.08)"
                      : `0 2px 10px ${alpha("#000", 0.05)}`,
                    transition: "border-color 0.25s, box-shadow 0.25s, background-color 0.25s",
                    "&:hover": {
                      borderColor: alpha(c.primary, 0.35),
                      boxShadow: isDark
                        ? `0 10px 32px rgba(8,8,15,0.4), 0 0 0 1px ${alpha(c.primary, 0.15)}, inset 0 1px 0 rgba(255,255,255,0.1)`
                        : `0 8px 20px ${alpha("#000", 0.08)}, 0 0 0 1px ${alpha(c.primary, 0.12)}`,
                    },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                    <Typography
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.62rem",
                        fontWeight: 800,
                        color: alpha(c.primary, 0.65),
                        letterSpacing: "0.05em",
                      }}
                    >
                      {step.number}
                    </Typography>
                    <Box
                      sx={{
                        width: 32,
                        height: 32,
                        borderRadius: 1.25,
                        bgcolor: alpha(c.primary, 0.14),
                        border: `1px solid ${alpha(c.primary, 0.3)}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: `0 0 12px ${alpha(c.primary, isDark ? 0.2 : 0.12)}`,
                      }}
                    >
                      <Icon sx={{ color: c.primary, fontSize: 16 }} />
                    </Box>
                    <Typography
                      sx={{
                        fontWeight: 700,
                        color: c.textPrimary,
                        fontSize: "0.95rem",
                        letterSpacing: "-0.01em",
                      }}
                    >
                      {step.title}
                    </Typography>
                  </Box>

                  <Typography
                    sx={{ color: c.textSecondary, fontSize: "0.78rem", lineHeight: 1.55, flex: 1 }}
                  >
                    {step.body}
                  </Typography>

                  <StepDetail detail={step.detail} />
                </Box>
              </ScrollReveal>
            );
          })}
        </Box>
      </Container>
    </Box>
  );
}

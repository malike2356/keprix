"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import LinkIcon from "@mui/icons-material/Link";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import {
  getMarketingColors,
} from "@/components/marketing/marketing-section";

/** Dark-surface palette for glass cards (section may be light-toned). */
const CARD = getMarketingColors("dark");

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
        { prefix: "$", text: "docker compose up" },
      ],
    },
  },
  {
    number: "02",
    icon: LinkIcon,
    title: "Connect",
    body: "Point channels at your instance. No SaaS account or shared API keys.",
    detail: {
      type: "channels" as const,
      items: ["Telegram", "Discord", "Web UI", "REST API"],
    },
  },
  {
    number: "03",
    icon: AutoFixHighIcon,
    title: "Mutate",
    body: "Ask for something new. Keprix synthesises a tool, shows the diff, and installs after approval.",
    detail: {
      type: "conversation" as const,
      lines: [
        { role: "user", text: "Track my hours on this project" },
        { role: "agent", text: "Synthesising time_tracker tool..." },
        { role: "system", text: "DIFF: +47 lines" },
        { role: "agent", text: "Approve? [Y/n]" },
      ],
    },
  },
] as const;

const ROLE_COLORS: Record<string, string> = {
  user: "rgba(96,165,250,0.9)",
  agent: alpha(CARD.primary, 0.9),
  system: "rgba(251,191,36,0.9)",
};

function StepDetail({
  detail,
}: {
  detail: (typeof STEPS)[number]["detail"];
}) {
  if (detail.type === "code") {
    return (
      <Box
        sx={{
          mt: "auto",
          p: 1.25,
          bgcolor: "rgba(6,6,14,0.8)",
          border: `1px solid rgba(255,255,255,0.07)`,
          borderRadius: 1.5,
          fontFamily: "monospace",
          fontSize: "0.62rem",
          lineHeight: 1.6,
        }}
      >
        {detail.lines.map((line) => (
          <Box key={line.text} sx={{ display: "flex", gap: 1.25 }}>
            <Box component="span" sx={{ color: alpha(CARD.primary, 0.85), flexShrink: 0 }}>
              {line.prefix}
            </Box>
            <Box component="span" sx={{ color: "rgba(237,237,248,0.95)", wordBreak: "break-all" }}>
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
              color: CARD.textPrimary,
              bgcolor: "rgba(255,255,255,0.06)",
              border: `1px solid rgba(255,255,255,0.14)`,
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
          bgcolor: "rgba(6,6,14,0.8)",
          border: "1px solid rgba(255,255,255,0.07)",
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
                color: ROLE_COLORS[line.role] ?? CARD.textSecondary,
                flexShrink: 0,
                minWidth: 34,
                textTransform: "uppercase",
                fontSize: "0.55rem",
                fontWeight: 700,
              }}
            >
              {line.role === "user" ? "you" : line.role === "agent" ? "agent" : "sys"}
            </Box>
            <Box component="span" sx={{ color: "rgba(237,237,248,0.92)" }}>
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
                fontSize: "0.8rem",
                fontWeight: 700,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: c.secondary,
                mb: 2,
              }}
            >
              Getting started
            </Typography>
            <Typography
              component="h2"
              sx={{
                fontSize: { xs: "2rem", md: "2.75rem" },
                fontWeight: 800,
                letterSpacing: "-0.03em",
                lineHeight: 1.15,
                mb: 2,
                color: c.textPrimary,
              }}
            >
              Up and running in minutes.
            </Typography>
            <Typography
              sx={{ color: c.textSecondary, maxWidth: 440, mx: "auto", fontSize: "1rem", lineHeight: 1.7 }}
            >
              Deploy locally, connect your channels, then extend capabilities on demand.
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
                    bgcolor: CARD.bgCard,
                    border: "1px solid rgba(255,255,255,0.1)",
                    position: "relative",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    gap: 1.5,
                    boxShadow: "0 6px 24px rgba(8,8,15,0.3), inset 0 1px 0 rgba(255,255,255,0.08)",
                    transition: "border-color 0.25s, box-shadow 0.25s",
                    "&:hover": {
                      borderColor: alpha(CARD.primary, 0.35),
                      boxShadow: `0 10px 32px rgba(8,8,15,0.4), 0 0 0 1px ${alpha(CARD.primary, 0.15)}, inset 0 1px 0 rgba(255,255,255,0.1)`,
                    },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                    <Typography
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.62rem",
                        fontWeight: 800,
                        color: alpha(CARD.primary, 0.65),
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
                        bgcolor: alpha(CARD.primary, 0.14),
                        border: `1px solid ${alpha(CARD.primary, 0.3)}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: `0 0 12px ${alpha(CARD.primary, 0.2)}`,
                      }}
                    >
                      <Icon sx={{ color: CARD.primary, fontSize: 16 }} />
                    </Box>
                    <Typography
                      sx={{
                        fontWeight: 700,
                        color: CARD.textPrimary,
                        fontSize: "0.95rem",
                        letterSpacing: "-0.01em",
                      }}
                    >
                      {step.title}
                    </Typography>
                  </Box>

                  <Typography
                    sx={{ color: CARD.textSecondary, fontSize: "0.78rem", lineHeight: 1.55, flex: 1 }}
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

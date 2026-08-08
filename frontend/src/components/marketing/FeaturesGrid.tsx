"use client";

import dynamic from "next/dynamic";
import * as React from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import CodeIcon from "@mui/icons-material/Code";
import HubIcon from "@mui/icons-material/Hub";
import MemoryIcon from "@mui/icons-material/Memory";
import ListAltIcon from "@mui/icons-material/ListAlt";
import ShieldIcon from "@mui/icons-material/Shield";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const DottedSurfaceBackground = dynamic(
  () => import("@/components/ui/dotted-surface-background").then((mod) => mod.DottedSurfaceBackground),
  { ssr: false },
);

function GlowCard({
  children,
  glowColor,
}: {
  children: React.ReactNode;
  glowColor: string;
}) {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";
  const [tilt, setTilt] = React.useState({ x: 0, y: 0 });
  const [hovered, setHovered] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  function onMove(e: React.MouseEvent) {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const cx = (e.clientX - r.left) / r.width - 0.5;
    const cy = (e.clientY - r.top) / r.height - 0.5;
    setTilt({ x: cy * -9, y: cx * 9 });
  }

  return (
    <Box
      ref={ref}
      onMouseMove={onMove}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setTilt({ x: 0, y: 0 }); }}
      sx={{
        position: "relative",
        height: "100%",
        transform: `perspective(900px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg) ${hovered ? "translateZ(6px)" : ""}`,
        transition: hovered ? "transform 0.08s linear" : "transform 0.5s ease",
        willChange: "transform",
      }}
    >
      {/* Ambient glow behind card */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          inset: -16,
          borderRadius: 3,
          background: `radial-gradient(ellipse at center, ${alpha(glowColor, isDark ? 0.22 : 0.14)} 0%, transparent 72%)`,
          filter: "blur(18px)",
          opacity: hovered ? 1 : 0,
          transition: "opacity 0.35s",
          pointerEvents: "none",
          zIndex: -1,
        }}
      />

      {/* Card */}
      <Box
        sx={{
          height: "100%",
          borderRadius: 2.5,
          p: 3.5,
          bgcolor: isDark ? "rgba(12,12,24,0.7)" : c.bgPaper,
          border: `1px solid ${hovered ? alpha(glowColor, 0.35) : isDark ? "rgba(255,255,255,0.07)" : c.divider}`,
          backdropFilter: isDark ? "blur(24px)" : "none",
          position: "relative",
          overflow: "hidden",
          transition: "border-color 0.25s, background-color 0.25s ease",
          boxShadow: hovered
            ? isDark
              ? `0 20px 48px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1)`
              : `0 12px 28px ${alpha("#000", 0.08)}, 0 0 0 1px ${alpha(glowColor, 0.12)}`
            : isDark
              ? `0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)`
              : `0 2px 10px ${alpha("#000", 0.05)}`,
        }}
      >
        {/* Specular gloss at top-left */}
        {isDark ? (
          <Box
            aria-hidden
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "50%",
              background:
                "linear-gradient(160deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.015) 40%, transparent 70%)",
              pointerEvents: "none",
              borderRadius: "10px 10px 0 0",
            }}
          />
        ) : null}
        {children}
      </Box>
    </Box>
  );
}

export function FeaturesGrid() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";

  const features = [
    {
      icon: CodeIcon,
      title: "Command Center TUI",
      body:
        "Run Keprix from a keyboard-first terminal with live sessions, slash commands, tool cards, review mode, and full diagnostics.",
      color: "#7c3aed",
    },
    {
      icon: HubIcon,
      title: "Agent OS runtime",
      body:
        "Operate action boards, run ledgers, agent apps, skills, plugins, playbooks, and workflows inside one shared secure self-hosted runtime.",
      color: "#06b6d4",
    },
    {
      icon: ShieldIcon,
      title: "Channel Shield layer",
      body:
        "Route inbound email and messaging through scanning, policies, sandboxing, quarantine, and safe summaries before anyone acts on them.",
      color: "#10b981",
    },
    {
      icon: MemoryIcon,
      title: "Long-term memory store",
      body:
        "Agents recall key facts across sessions in a structured store namespaced by workspace with full semantic search available.",
      color: "#f59e0b",
    },
    {
      icon: ListAltIcon,
      title: "Playbooks and triggers",
      body:
        "Compose visual or YAML workflows, schedule with cron, trigger from webhooks, and review each run through human approvals.",
      color: "#ef4444",
    },
    {
      icon: AutoFixHighIcon,
      title: "Reviewable self coding",
      body:
        "The agent proposes tools and repo changes; you inspect diffs, tests, and risk before anything ever lands live.",
      color: "#8b5cf6",
    },
  ] as const;

  return (
    <Box
      id="features"
      sx={{
        py: { xs: 12, md: 16 },
        position: "relative",
        overflow: "hidden",
        bgcolor: c.bgDefault,
      }}
    >
      <DottedSurfaceBackground mode={isDark ? "dark" : "light"} />

      <Box
        aria-hidden
        sx={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
          pointerEvents: "none",
          background: isDark
            ? `
            radial-gradient(ellipse at 50% 35%, ${alpha(c.primary, 0.08)} 0%, transparent 45%),
            radial-gradient(ellipse at 50% 100%, ${alpha(c.bgDefault, 0.35)} 0%, transparent 65%)
          `
            : `
            radial-gradient(ellipse at 50% 0%, ${alpha(c.primary, 0.1)} 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, ${alpha(c.secondary, 0.08)} 0%, transparent 45%)
          `,
        }}
      />

      {/* Ambient top glow */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: -200,
          left: "50%",
          transform: "translateX(-50%)",
          width: 900,
          height: 600,
          borderRadius: "50%",
          background: `radial-gradient(ellipse at center, ${alpha(c.primary, 0.09)} 0%, transparent 70%)`,
          pointerEvents: "none",
        }}
      />

      <Container maxWidth="lg" sx={{ position: "relative", zIndex: 1 }}>
        <ScrollReveal>
          <Box sx={{ textAlign: "center", mb: 10 }}>
            <Typography
              component="p"
              sx={{
                ...MARKETING_EYEBROW_SX,
                color: c.primary,
                mb: 2,
              }}
            >
              Capabilities
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
              Everything your agent needs,
              <br />
              in one runtime.
            </Typography>
            <Typography
              sx={{ color: c.textSecondary, maxWidth: 480, mx: "auto", fontSize: "1rem", lineHeight: 1.7 }}
            >
              Self-hosted. MIT licensed. No vendor lock-in.
            </Typography>
          </Box>
        </ScrollReveal>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr" },
            gap: 2.5,
          }}
        >
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <ScrollReveal key={f.title} delay={i * 0.07}>
                <Box sx={{ height: "100%" }}>
                  <GlowCard glowColor={f.color}>
                    {/* Icon with point glow */}
                    <Box sx={{ position: "relative", mb: 3, display: "inline-flex" }}>
                      <Box
                        aria-hidden
                        sx={{
                          position: "absolute",
                          inset: -8,
                          borderRadius: "50%",
                          background: `radial-gradient(circle, ${alpha(f.color, 0.4)} 0%, transparent 70%)`,
                          filter: "blur(8px)",
                        }}
                      />
                      <Box
                        sx={{
                          width: 48,
                          height: 48,
                          borderRadius: 2,
                          bgcolor: alpha(f.color, 0.1),
                          border: `1px solid ${alpha(f.color, 0.25)}`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          position: "relative",
                        }}
                      >
                        <Icon sx={{ color: f.color, fontSize: 22 }} />
                      </Box>
                    </Box>

                    <Typography
                      sx={{
                        fontWeight: 700,
                        color: c.textPrimary,
                        mb: 1.25,
                        fontSize: "1.05rem",
                        letterSpacing: "-0.01em",
                      }}
                    >
                      {f.title}
                    </Typography>
                    <Typography
                      sx={{ fontSize: "0.875rem", color: c.textSecondary, lineHeight: 1.7 }}
                    >
                      {f.body}
                    </Typography>
                  </GlowCard>
                </Box>
              </ScrollReveal>
            );
          })}
        </Box>
      </Container>
    </Box>
  );
}

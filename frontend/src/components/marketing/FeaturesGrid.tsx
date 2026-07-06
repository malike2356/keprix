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
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

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
          background: `radial-gradient(ellipse at center, ${alpha(glowColor, 0.22)} 0%, transparent 72%)`,
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
          bgcolor: "rgba(12,12,24,0.7)",
          border: `1px solid ${hovered ? alpha(glowColor, 0.3) : "rgba(255,255,255,0.07)"}`,
          backdropFilter: "blur(24px)",
          position: "relative",
          overflow: "hidden",
          transition: "border-color 0.25s",
          boxShadow: hovered
            ? `0 20px 48px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1)`
            : `0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)`,
        }}
      >
        {/* Specular gloss at top-left */}
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
        {children}
      </Box>
    </Box>
  );
}

export function FeaturesGrid() {
  const c = useMarketingColors();

  const features = [
    {
      icon: AutoFixHighIcon,
      title: "Mutation Engine",
      body:
        "When the agent needs a tool that does not exist, it synthesises Python code in a sandbox, shows you the diff, and waits for your approval before installing. No manual plugin writing.",
      color: "#7c3aed",
    },
    {
      icon: CodeIcon,
      title: "Self-coding workspace",
      body:
        "Give the agent a repo and a task. It plans, writes code, runs tests in an isolated container, and iterates until green. You review a PR, not a pile of instructions.",
      color: "#06b6d4",
    },
    {
      icon: HubIcon,
      title: "Multi-channel inbox",
      body:
        "Connect Telegram, Discord, Slack, WhatsApp, email, and webhooks to one runtime. Each channel routes to the right agent persona with its own memory and tool set.",
      color: "#10b981",
    },
    {
      icon: MemoryIcon,
      title: "Long-term memory",
      body:
        "Structured memory store backed by PostgreSQL or SQLite. Agents recall facts across sessions, namespaced by workspace. Semantic search via pgvector when available.",
      color: "#f59e0b",
    },
    {
      icon: ListAltIcon,
      title: "Playbooks",
      body:
        "Compose deterministic workflows in YAML. Chain tools, conditions, and agent calls. Schedule them with cron or trigger via webhook. No separate orchestration layer needed.",
      color: "#ef4444",
    },
    {
      icon: ShieldIcon,
      title: "Full observability",
      body:
        "Every LLM call, tool execution, and mutation event is logged with latency, token cost, and trace ID. Budget alerts fire before you exceed your monthly threshold.",
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
      <DottedSurfaceBackground />

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
                fontSize: "0.8rem",
                fontWeight: 700,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: c.primary,
                mb: 2,
              }}
            >
              Capabilities
            </Typography>
            <Typography
              component="h2"
              sx={{
                fontSize: { xs: "2rem", md: "2.75rem" },
                fontWeight: 800,
                letterSpacing: "-0.03em",
                lineHeight: 1.15,
                mb: 2,
                background: `linear-gradient(140deg, ${c.textPrimary} 30%, ${alpha(c.primary, 0.85)} 100%)`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
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

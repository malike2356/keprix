"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import { alpha } from "@mui/material/styles";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import TerminalIcon from "@mui/icons-material/Terminal";
import LayersIcon from "@mui/icons-material/Layers";
import CodeIcon from "@mui/icons-material/Code";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import {
  MARKETING_DISPLAY_FONT,
  MARKETING_MONO_FONT,
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const INSTALL_METHODS = [
  {
    id: "curl",
    label: "Quick Install (curl)",
    icon: <TerminalIcon fontSize="small" />,
    summary: "One-line script installer for Linux, macOS, and WSL2. Sets up Python env and puts keprix on your PATH.",
    command: "curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash",
    nextSteps: [
      { step: "1", title: "Configure models", code: "keprix setup", desc: "Interactive wizard to connect your LLM provider key." },
      { step: "2", title: "Launch Command Center", code: "keprix tui", desc: "Interactive terminal UI with sessions, tools, and review." },
    ],
    details: [
      "Clones and updates under ~/.keprix/keprix",
      "Creates an isolated Python 3.11+ virtual environment",
      "Adds keprix CLI and Command Center TUI to ~/.local/bin",
    ],
  },
  {
    id: "docker",
    label: "Docker Compose",
    icon: <LayersIcon fontSize="small" />,
    summary: "Complete containerized stack: Next.js Web Workspace, FastAPI backend, PostgreSQL with pgvector, and Redis.",
    command: "git clone https://github.com/malike2356/keprix.git\ncd keprix\ncp .env.example .env\ndocker compose -f docker/docker-compose.yml up -d --build",
    nextSteps: [
      { step: "1", title: "Open Web Workspace", code: "http://localhost:3000", desc: "Full Next.js workspace UI: chat, playbooks, documents, settings." },
      { step: "2", title: "REST API & Docs", code: "http://localhost:3333/docs", desc: "FastAPI interactive OpenAPI docs and Swagger schema." },
    ],
    details: [
      "No host Python setup required; runs in Docker",
      "Isolated PostgreSQL 16 + pgvector database",
      "Production-ready compose setup with health checks",
    ],
  },
  {
    id: "pipx",
    label: "Python pipx",
    icon: <CodeIcon fontSize="small" />,
    summary: "Isolated Python application install directly from the public GitHub repository.",
    command: "pipx install 'keprix[tui] @ git+https://github.com/malike2356/keprix.git'",
    nextSteps: [
      { step: "1", title: "Verify install", code: "keprix --version", desc: "Check that keprix CLI is available on your shell PATH." },
      { step: "2", title: "Start TUI", code: "keprix tui", desc: "Launch the terminal Command Center interface." },
    ],
    details: [
      "Requires Python 3.11 or 3.12 and pipx installed",
      "Zero Docker footprint; purely CLI & TUI",
      "Easily upgraded with pipx upgrade keprix",
    ],
  },
] as const;

export function InstallSection() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";
  const [activeTab, setActiveTab] = React.useState(0);
  const [copied, setCopied] = React.useState(false);

  const activeMethod = INSTALL_METHODS[activeTab];

  const handleCopy = async (text: string) => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2200);
      }
    } catch {
      // ignore clipboard error
    }
  };

  return (
    <Box
      id="install"
      component="section"
      sx={{
        py: { xs: 10, md: 16 },
        position: "relative",
        overflow: "hidden",
        scrollMarginTop: 80,
        bgcolor: isDark ? "rgba(8, 10, 16, 0.95)" : alpha(c.bgDefault, 0.98),
        borderTop: `1px solid ${c.divider}`,
        borderBottom: `1px solid ${c.divider}`,
      }}
    >
      <span id="deploy" style={{ position: "absolute", top: -80, left: 0, height: 1, width: 1, opacity: 0 }} />

      {/* Background ambient glow */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: "20%",
          left: "50%",
          transform: "translateX(-50%)",
          width: 700,
          height: 400,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${alpha(c.primary, isDark ? 0.12 : 0.08)} 0%, transparent 70%)`,
          filter: "blur(60px)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <Container maxWidth="lg" sx={{ position: "relative", zIndex: 1 }}>
        <ScrollReveal>
          <Box sx={{ textAlign: "center", mb: 6 }}>
            <Box
              sx={{
                display: "inline-flex",
                alignItems: "center",
                gap: 1,
                px: 2,
                py: 0.75,
                mb: 2.5,
                borderRadius: 5,
                border: `1px solid ${alpha(c.primary, 0.35)}`,
                bgcolor: alpha(c.primary, 0.08),
              }}
            >
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  bgcolor: c.primary,
                  boxShadow: `0 0 8px ${c.primary}`,
                }}
              />
              <Typography sx={{ ...MARKETING_EYEBROW_SX, color: c.primary }}>
                Deploy Free - 100% Open Source
              </Typography>
            </Box>

            <Typography
              component="h2"
              sx={{
                ...MARKETING_HEADING_SX,
                fontFamily: MARKETING_DISPLAY_FONT,
                fontSize: { xs: "2.3rem", sm: "3rem", md: "3.6rem" },
                mb: 2,
                color: c.textPrimary,
              }}
            >
              Deploy Keprix on your own machine
            </Typography>

            <Typography
              sx={{
                color: c.textSecondary,
                fontSize: { xs: "0.95rem", md: "1.05rem" },
                maxWidth: 680,
                mx: "auto",
                lineHeight: 1.7,
              }}
            >
              Choose your preferred deployment method. Run agents, memory, playbooks, and Channel Shield
              on your own hardware or VPS in under two minutes.
            </Typography>
          </Box>

          {/* Method selector tabs */}
          <Box sx={{ display: "flex", justifyContent: "center", mb: 4 }}>
            <Tabs
              value={activeTab}
              onChange={(_e, val) => {
                setActiveTab(val);
                setCopied(false);
              }}
              variant="scrollable"
              scrollButtons="auto"
              sx={{
                bgcolor: isDark ? alpha("#fff", 0.04) : alpha(c.bgPaper, 0.7),
                p: 0.5,
                borderRadius: 3,
                border: `1px solid ${alpha(c.divider, 0.8)}`,
                "& .MuiTabs-indicator": {
                  bgcolor: c.primary,
                  height: 3,
                  borderRadius: 1.5,
                },
              }}
            >
              {INSTALL_METHODS.map((method, idx) => (
                <Tab
                  key={method.id}
                  label={method.label}
                  icon={method.icon}
                  iconPosition="start"
                  sx={{
                    fontWeight: activeTab === idx ? 700 : 500,
                    fontSize: "0.875rem",
                    color: activeTab === idx ? c.primary : c.textSecondary,
                    minHeight: 44,
                    px: { xs: 2, sm: 3 },
                    borderRadius: 2,
                    textTransform: "none",
                    "&.Mui-selected": {
                      color: c.primary,
                      bgcolor: alpha(c.primary, 0.08),
                    },
                  }}
                />
              ))}
            </Tabs>
          </Box>

          {/* Main Terminal Command Card */}
          <Card
            sx={{
              maxWidth: 880,
              mx: "auto",
              bgcolor: isDark ? "rgba(12, 14, 24, 0.95)" : "#0f141c",
              color: "#f0f6fc",
              border: `1px solid ${alpha(c.primary, 0.35)}`,
              borderRadius: 3.5,
              boxShadow: `0 8px 32px ${alpha("#000", isDark ? 0.6 : 0.2)}, 0 0 40px ${alpha(c.primary, 0.1)}`,
              overflow: "hidden",
            }}
          >
            {/* Window header */}
            <Box
              sx={{
                px: 2.5,
                py: 1.25,
                bgcolor: "rgba(255, 255, 255, 0.04)",
                borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box sx={{ width: 11, height: 11, borderRadius: "50%", bgcolor: "#ff5f57" }} />
                <Box sx={{ width: 11, height: 11, borderRadius: "50%", bgcolor: "#febc2e" }} />
                <Box sx={{ width: 11, height: 11, borderRadius: "50%", bgcolor: "#28c840" }} />
                <Typography
                  sx={{
                    ml: 1.5,
                    fontSize: "0.75rem",
                    color: "rgba(255, 255, 255, 0.5)",
                    fontFamily: MARKETING_MONO_FONT,
                  }}
                >
                  terminal - {activeMethod.id}
                </Typography>
              </Box>

              <Tooltip title={copied ? "Copied to clipboard!" : "Copy command"}>
                <Button
                  onClick={() => handleCopy(activeMethod.command)}
                  size="small"
                  startIcon={copied ? <CheckIcon fontSize="small" sx={{ color: "#3fb950" }} /> : <ContentCopyIcon fontSize="small" />}
                  sx={{
                    color: copied ? "#3fb950" : "rgba(255, 255, 255, 0.8)",
                    bgcolor: copied ? "rgba(63, 185, 80, 0.15)" : "rgba(255, 255, 255, 0.08)",
                    border: `1px solid ${copied ? "rgba(63, 185, 80, 0.4)" : "rgba(255, 255, 255, 0.12)"}`,
                    borderRadius: 2,
                    textTransform: "none",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    px: 1.75,
                    "&:hover": {
                      bgcolor: "rgba(255, 255, 255, 0.15)",
                    },
                  }}
                >
                  {copied ? "Copied" : "Copy command"}
                </Button>
              </Tooltip>
            </Box>

            {/* Command area */}
            <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
              <Typography
                sx={{
                  color: "rgba(255, 255, 255, 0.65)",
                  fontSize: "0.85rem",
                  mb: 2,
                  lineHeight: 1.5,
                }}
              >
                {activeMethod.summary}
              </Typography>

              <Box
                sx={{
                  position: "relative",
                  bgcolor: "rgba(0, 0, 0, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  borderRadius: 2,
                  p: 2,
                  overflowX: "auto",
                }}
              >
                <Box
                  component="pre"
                  sx={{
                    m: 0,
                    fontFamily: MARKETING_MONO_FONT,
                    fontSize: { xs: "0.8rem", sm: "0.875rem" },
                    lineHeight: 1.7,
                    color: "#58a6ff",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                  }}
                >
                  <Typography component="span" sx={{ color: "#7ee787", mr: 1, userSelect: "none" }}>
                    $
                  </Typography>
                  {activeMethod.command}
                </Box>
              </Box>

              {/* Next steps */}
              <Box sx={{ mt: 3 }}>
                <Typography
                  sx={{
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "rgba(255, 255, 255, 0.5)",
                    mb: 1.5,
                  }}
                >
                  Next steps after installation:
                </Typography>
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
                  {activeMethod.nextSteps.map((step) => (
                    <Box
                      key={step.step}
                      sx={{
                        p: 1.75,
                        borderRadius: 2,
                        bgcolor: "rgba(255, 255, 255, 0.03)",
                        border: "1px solid rgba(255, 255, 255, 0.06)",
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                        <Box
                          sx={{
                            width: 20,
                            height: 20,
                            borderRadius: "50%",
                            bgcolor: alpha(c.primary, 0.25),
                            color: "#fff",
                            fontSize: "0.7rem",
                            fontWeight: 700,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          {step.step}
                        </Box>
                        <Typography sx={{ fontSize: "0.8rem", fontWeight: 600, color: "rgba(255, 255, 255, 0.9)" }}>
                          {step.title}
                        </Typography>
                      </Box>
                      <Box
                        component="code"
                        sx={{
                          display: "block",
                          fontFamily: MARKETING_MONO_FONT,
                          fontSize: "0.775rem",
                          color: "#7ee787",
                          bgcolor: "rgba(0, 0, 0, 0.3)",
                          p: 0.75,
                          borderRadius: 1,
                          mb: 0.5,
                          overflowX: "auto",
                        }}
                      >
                        {step.code}
                      </Box>
                      <Typography sx={{ fontSize: "0.725rem", color: "rgba(255, 255, 255, 0.55)" }}>
                        {step.desc}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>

              {/* Bullet notes */}
              <Box sx={{ mt: 3, pt: 2.5, borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                  {activeMethod.details.map((detail, idx) => (
                    <Box key={idx} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <CheckIcon sx={{ color: "#3fb950", fontSize: 16 }} />
                      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255, 255, 255, 0.7)" }}>
                        {detail}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Box>
          </Card>

          {/* Highlights row */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" },
              gap: 2.5,
              maxWidth: 880,
              mx: "auto",
              mt: 4,
            }}
          >
            <Card
              sx={{
                p: 2.5,
                borderRadius: 2.5,
                bgcolor: isDark ? alpha("#fff", 0.02) : alpha(c.bgCard, 0.8),
                border: `1px solid ${alpha(c.divider, 0.7)}`,
              }}
            >
              <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                <Typography sx={{ fontWeight: 700, fontSize: "0.9rem", color: c.textPrimary, mb: 0.75 }}>
                  100% MIT Licensed
                </Typography>
                <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary, lineHeight: 1.6 }}>
                  Free forever for personal, team, or commercial use. No feature paywalls, license keys, or seat limits.
                </Typography>
              </CardContent>
            </Card>

            <Card
              sx={{
                p: 2.5,
                borderRadius: 2.5,
                bgcolor: isDark ? alpha("#fff", 0.02) : alpha(c.bgCard, 0.8),
                border: `1px solid ${alpha(c.divider, 0.7)}`,
              }}
            >
              <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                <Typography sx={{ fontWeight: 700, fontSize: "0.9rem", color: c.textPrimary, mb: 0.75 }}>
                  Private &amp; Self-Hosted
                </Typography>
                <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary, lineHeight: 1.6 }}>
                  All conversations, long-term memory, documents, and credentials remain strictly on your machine.
                </Typography>
              </CardContent>
            </Card>

            <Card
              sx={{
                p: 2.5,
                borderRadius: 2.5,
                bgcolor: isDark ? alpha("#fff", 0.02) : alpha(c.bgCard, 0.8),
                border: `1px solid ${alpha(c.divider, 0.7)}`,
              }}
            >
              <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                <Typography sx={{ fontWeight: 700, fontSize: "0.9rem", color: c.textPrimary, mb: 0.75 }}>
                  Multiple Surfaces
                </Typography>
                <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary, lineHeight: 1.6 }}>
                  Operate from the Command Center TUI, browser Next.js workspace, REST API, or Universal Sidecar.
                </Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Further resources buttons */}
          <Box
            sx={{
              mt: 5,
              display: "flex",
              justifyContent: "center",
              gap: 2,
              flexWrap: "wrap",
            }}
          >
            <Button
              component="a"
              href="/docs"
              variant="outlined"
              endIcon={<ArrowForwardIcon fontSize="small" />}
              sx={{
                fontWeight: 600,
                borderRadius: 999,
                px: 3,
                borderColor: alpha(c.divider, 0.8),
                color: c.textSecondary,
                "&:hover": {
                  borderColor: c.primary,
                  color: c.textPrimary,
                  bgcolor: alpha(c.primary, 0.06),
                },
              }}
            >
              Installation documentation
            </Button>
            <Button
              component="a"
              href="/download"
              variant="outlined"
              endIcon={<ArrowForwardIcon fontSize="small" />}
              sx={{
                fontWeight: 600,
                borderRadius: 999,
                px: 3,
                borderColor: alpha(c.divider, 0.8),
                color: c.textSecondary,
                "&:hover": {
                  borderColor: c.primary,
                  color: c.textPrimary,
                  bgcolor: alpha(c.primary, 0.06),
                },
              }}
            >
              Offline packages &amp; verification
            </Button>
            <Button
              component="a"
              href="https://github.com/malike2356/keprix"
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              endIcon={<OpenInNewIcon fontSize="small" />}
              sx={{
                fontWeight: 600,
                borderRadius: 999,
                px: 3,
                borderColor: alpha(c.divider, 0.8),
                color: c.textSecondary,
                "&:hover": {
                  borderColor: c.primary,
                  color: c.textPrimary,
                  bgcolor: alpha(c.primary, 0.06),
                },
              }}
            >
              GitHub repository
            </Button>
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}

"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import { alpha } from "@mui/material/styles";
import Link from "next/link";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import { InfiniteSlider } from "@/components/ui/InfiniteSlider";

const WovenHeroBackground = dynamic(
  () => import("@/components/ui/woven-light-hero").then((mod) => mod.WovenHeroBackground),
  { ssr: false },
);

const TERMINAL_LINES = [
  { prefix: "$", text: "docker compose up keprix" },
  { prefix: ">", text: "Creating developer identity..." },
  { prefix: ">", text: "Starting agent runtime on :3333" },
  { prefix: ">", text: "Keprix v1.0.0 ready." },
  { prefix: "[User]", text: "Track my time on this project" },
  { prefix: "[Keprix]", text: "No time-tracking tool found. Synthesising..." },
  { prefix: "[Keprix]", text: "Sandbox passed. Approve? [Y/n]" },
  { prefix: "[User]", text: "Y" },
  { prefix: "[Keprix]", text: "Installed. Tracking started." },
] as const;

const STACK_ITEMS = [
  "Anthropic",
  "OpenAI",
  "Gemini",
  "Ollama",
  "Groq",
  "Telegram",
  "Discord",
  "Docker",
] as const;

const CHAR_DELAY_MS = 26;
const LINE_PAUSE_MS = 140;
const LOOP_HOLD_MS = 2800;
const BOOT_DELAY_MS = 500;

function TerminalCursor() {
  return (
    <Box
      component="span"
      sx={{
        display: "inline-block",
        width: 8,
        height: "1em",
        ml: 0.25,
        bgcolor: KEPRIX_COLORS.primary,
        animation: "blink 1s step-end infinite",
        "@keyframes blink": { "0%,100%": { opacity: 1 }, "50%": { opacity: 0 } },
        verticalAlign: "text-bottom",
      }}
    />
  );
}

function TerminalWindow() {
  const [lineIndex, setLineIndex] = React.useState(0);
  const [charIndex, setCharIndex] = React.useState(0);
  const [cycle, setCycle] = React.useState(0);
  const [booting, setBooting] = React.useState(true);
  const [reducedMotion, setReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReducedMotion(reduced);
    if (reduced) {
      setBooting(false);
      setLineIndex(TERMINAL_LINES.length - 1);
      setCharIndex(TERMINAL_LINES[TERMINAL_LINES.length - 1].text.length);
    }
  }, []);

  React.useEffect(() => {
    if (reducedMotion) return;

    if (booting) {
      const bootTimer = window.setTimeout(() => setBooting(false), BOOT_DELAY_MS);
      return () => window.clearTimeout(bootTimer);
    }

    const line = TERMINAL_LINES[lineIndex];
    const isLastLine = lineIndex === TERMINAL_LINES.length - 1;
    const lineComplete = charIndex >= line.text.length;

    if (!lineComplete) {
      const typeTimer = window.setTimeout(() => setCharIndex((value) => value + 1), CHAR_DELAY_MS);
      return () => window.clearTimeout(typeTimer);
    }

    if (!isLastLine) {
      const nextLineTimer = window.setTimeout(() => {
        setLineIndex((value) => value + 1);
        setCharIndex(0);
      }, LINE_PAUSE_MS);
      return () => window.clearTimeout(nextLineTimer);
    }

    const loopTimer = window.setTimeout(() => {
      setBooting(true);
      setLineIndex(0);
      setCharIndex(0);
      setCycle((value) => value + 1);
    }, LOOP_HOLD_MS);
    return () => window.clearTimeout(loopTimer);
  }, [booting, lineIndex, charIndex, cycle, reducedMotion]);

  const visibleLines = booting
    ? []
    : TERMINAL_LINES.slice(0, lineIndex + 1).map((line, index) => ({
        ...line,
        text: index < lineIndex ? line.text : line.text.slice(0, charIndex),
      }));

  return (
    <Box
      role="img"
      aria-label="Keprix terminal demo"
      sx={{
        bgcolor: "rgba(10,12,20,0.85)",
        border: `1px solid ${alpha(KEPRIX_COLORS.primary, 0.3)}`,
        borderRadius: 3,
        overflow: "hidden",
        fontFamily: "monospace",
        fontSize: { xs: "0.75rem", sm: "0.85rem" },
        lineHeight: 1.7,
        backdropFilter: "blur(12px)",
        boxShadow: `0 0 60px ${alpha(KEPRIX_COLORS.primary, 0.18)}, 0 24px 64px rgba(0,0,0,0.6)`,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1,
          bgcolor: alpha("#fff", 0.04),
          borderBottom: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.5)}`,
          display: "flex",
          gap: 0.75,
          alignItems: "center",
        }}
      >
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <Box key={c} sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: c }} />
        ))}
        <Typography
          sx={{ ml: 1, fontSize: "0.7rem", color: alpha("#fff", 0.4), fontFamily: "monospace" }}
        >
          keprix - mutation engine
        </Typography>
      </Box>

      <Box sx={{ p: { xs: 2, sm: 3 }, minHeight: { xs: 220, sm: 260 } }}>
        {visibleLines.map((line, i) => {
          const isUser = line.prefix === "[User]";
          const isKeprix = line.prefix === "[Keprix]";
          const prefixColor = isUser
            ? "#58a6ff"
            : isKeprix
            ? KEPRIX_COLORS.primary
            : alpha("#fff", 0.5);
          const isActiveLine = i === lineIndex && !booting;

          return (
            <Box key={`${cycle}-${i}`} sx={{ display: "flex", gap: 1, mb: 0.5 }}>
              <Typography
                component="span"
                sx={{ color: prefixColor, fontFamily: "monospace", whiteSpace: "nowrap", fontSize: "inherit" }}
              >
                {line.prefix}
              </Typography>
              <Typography
                component="span"
                sx={{ color: alpha("#e6edf3", 0.9), fontFamily: "monospace", fontSize: "inherit" }}
              >
                {line.text}
                {isActiveLine && <TerminalCursor />}
              </Typography>
            </Box>
          );
        })}
        {booting && <TerminalCursor />}
      </Box>
    </Box>
  );
}

export function Hero() {
  return (
    <>
      {/* Hero section */}
      <Box
        component="section"
        sx={{
          position: "relative",
          overflow: "hidden",
          minHeight: { xs: "100vh", md: "95vh" },
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          bgcolor: "#0a0a10",
        }}
      >
        <WovenHeroBackground />

        {/* Readability overlay */}
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            inset: 0,
            zIndex: 0,
            background: `
              radial-gradient(ellipse 80% 60% at 50% 20%, rgba(10,10,16,0.35) 0%, rgba(10,10,16,0.72) 70%),
              linear-gradient(to bottom, rgba(10,10,16,0.2) 0%, rgba(10,10,16,0.85) 100%)
            `,
            pointerEvents: "none",
          }}
        />

        {/* Content */}
        <Container
          maxWidth="lg"
          sx={{
            position: "relative",
            zIndex: 1,
            pt: { xs: 16, md: 20 },
            pb: { xs: 10, md: 14 },
          }}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
              gap: { xs: 6, lg: 8 },
              alignItems: "center",
            }}
          >
            {/* Left: copy */}
            <Box>
              <Chip
                label="Open source - MIT license"
                size="small"
                sx={{
                  mb: 2,
                  bgcolor: alpha(KEPRIX_COLORS.primary, 0.12),
                  color: KEPRIX_COLORS.primary,
                  border: `1px solid ${alpha(KEPRIX_COLORS.primary, 0.3)}`,
                  fontWeight: 600,
                  fontSize: "0.75rem",
                }}
              />
              <Typography
                component="p"
                sx={{
                  fontSize: { xs: "0.95rem", md: "1.05rem" },
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  color: KEPRIX_COLORS.secondary,
                  mb: 1.5,
                }}
              >
                Mutation engine + self-coding agent
              </Typography>
              <Typography
                component="h1"
                sx={{
                  fontSize: { xs: "2.75rem", sm: "3.5rem", md: "4rem", lg: "4.25rem" },
                  fontWeight: 800,
                  lineHeight: 1.08,
                  letterSpacing: "-0.035em",
                  color: KEPRIX_COLORS.textPrimary,
                  mb: 2,
                }}
              >
                The self-hosted agent OS
                <Box
                  component="span"
                  sx={{ display: "block", color: KEPRIX_COLORS.primary }}
                >
                  that grows new tools on demand.
                </Box>
              </Typography>
              <Typography
                sx={{
                  fontSize: { xs: "1rem", md: "1.0625rem" },
                  color: alpha(KEPRIX_COLORS.textPrimary, 0.86),
                  lineHeight: 1.75,
                  mb: 4,
                  maxWidth: 520,
                }}
              >
                Synthesises sandboxed Python tools after your approval, or edits and tests full repos
                in the self-coding workspace.
              </Typography>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Button
                  component={Link}
                  href="/auth/setup"
                  variant="contained"
                  size="large"
                  sx={{
                    fontWeight: 700,
                    px: 3.5,
                    borderRadius: "9999px",
                    background: `linear-gradient(135deg, ${KEPRIX_COLORS.primary} 0%, ${KEPRIX_COLORS.secondary} 100%)`,
                    boxShadow: `0 4px 24px ${alpha(KEPRIX_COLORS.primary, 0.4)}`,
                    "&:hover": {
                      boxShadow: `0 6px 32px ${alpha(KEPRIX_COLORS.primary, 0.55)}`,
                    },
                  }}
                >
                  Deploy in 2 minutes
                </Button>
                <Button
                  component="a"
                  href="https://github.com/malike2356/keprix"
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="outlined"
                  size="large"
                  sx={{
                    fontWeight: 600,
                    px: 3.5,
                    borderRadius: "9999px",
                    borderColor: alpha(KEPRIX_COLORS.divider, 0.6),
                    color: KEPRIX_COLORS.textSecondary,
                    "&:hover": {
                      borderColor: KEPRIX_COLORS.primary,
                      color: KEPRIX_COLORS.textPrimary,
                      bgcolor: alpha(KEPRIX_COLORS.primary, 0.06),
                    },
                  }}
                >
                  View on GitHub
                </Button>
              </Box>
            </Box>

            {/* Right: terminal */}
            <Box sx={{ position: "relative" }}>
              <TerminalWindow />
              {/* Subtle glow behind terminal */}
              <Box
                aria-hidden
                sx={{
                  position: "absolute",
                  inset: "-20%",
                  background: `radial-gradient(ellipse at center, ${alpha(KEPRIX_COLORS.primary, 0.1)} 0%, transparent 70%)`,
                  pointerEvents: "none",
                  zIndex: -1,
                }}
              />
            </Box>
          </Box>
        </Container>

        {/* Bottom fade into stack band */}
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 96,
            background: "linear-gradient(to bottom, transparent 0%, rgba(10,10,16,1) 100%)",
            pointerEvents: "none",
          }}
        />
      </Box>

      {/* Infinite logo slider section */}
      <Box
        component="section"
        sx={{
          bgcolor: "rgba(10,10,16,1)",
          py: 4,
          borderBottom: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.4)}`,
        }}
      >
        <Container maxWidth="lg">
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              alignItems: "center",
              gap: { xs: 3, md: 0 },
            }}
          >
            <Box
              sx={{
                flexShrink: 0,
                textAlign: { xs: "center", md: "right" },
                pr: { md: 4 },
                borderRight: { md: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.4)}` },
                minWidth: { md: 160 },
              }}
            >
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: alpha(KEPRIX_COLORS.textPrimary, 0.72),
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  fontWeight: 700,
                  lineHeight: 1.4,
                }}
              >
                Works with
                <br />
                your stack
              </Typography>
            </Box>

            <Box sx={{ position: "relative", flex: 1, minWidth: 0, py: 1, overflow: "hidden" }}>
              <InfiniteSlider speedOnHover={80} speed={40} gap={48}>
                {STACK_ITEMS.map((name) => (
                  <Box
                    key={name}
                    sx={{
                      px: 2,
                      py: 0.75,
                      borderRadius: 999,
                      flexShrink: 0,
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      letterSpacing: "0.02em",
                      color: alpha(KEPRIX_COLORS.textPrimary, 0.88),
                      bgcolor: alpha("#fff", 0.06),
                      border: `1px solid ${alpha("#fff", 0.14)}`,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {name}
                  </Box>
                ))}
              </InfiniteSlider>
            </Box>
          </Box>
        </Container>
      </Box>
    </>
  );
}

"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import { alpha, keyframes } from "@mui/material/styles";
import Link from "next/link";
import * as React from "react";
import { KeprixLogo } from "@/components/shared/KeprixLogo";
import {
  getMarketingColors,
  MARKETING_DISPLAY_FONT,
  MARKETING_MONO_FONT,
} from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const blink = keyframes`
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
`;

const marqueeScroll = keyframes`
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
`;

type TerminalLine = {
  prefix: "$" | ">" | "[User]" | "[Keprix]";
  text: string;
};

const TERMINAL_LINES: TerminalLine[] = [
  { prefix: "$", text: "keprix tui" },
  { prefix: ">", text: "Runtime ready. Memory, tools, and policies loaded." },
  { prefix: "[User]", text: "Build a workflow to protect inbound client emails" },
  { prefix: "[Keprix]", text: "Missing protection layer detected." },
  { prefix: "[Keprix]", text: "Proposed: Channel Shield policy + quarantine flow." },
  { prefix: "[Keprix]", text: "Tests passed. Review risk report?" },
  { prefix: "[User]", text: "yes" },
  { prefix: "[Keprix]", text: "Waiting for approval before deployment." },
];

const USER_COLOR = "#58a6ff";
const KEPRIX_COLOR = "#bb9af7";

function typingDelay(line: TerminalLine, charIndex: number): number {
  if (line.prefix === "$") return 42;
  if (line.prefix === ">") return 22;
  if (line.prefix === "[User]") return line.text.length <= 4 ? 120 : 26;
  const ch = line.text[charIndex] ?? "";
  if (ch === "." || ch === "?") return 280;
  if (ch === " ") return 18;
  return 24;
}

function pauseAfterLine(line: TerminalLine): number {
  if (line.prefix === "$") return 520;
  if (line.prefix === ">") return 680;
  if (line.prefix === "[User]") return 420;
  return 520;
}

function TerminalCursor({ color }: { color: string }) {
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        display: "inline-block",
        width: "0.55em",
        height: "1.05em",
        ml: 0.25,
        bgcolor: color,
        verticalAlign: "text-bottom",
        animation: `${blink} 1s step-end infinite`,
      }}
    />
  );
}

function TerminalWindow() {
  const { mode } = useThemeMode();
  const colors = getMarketingColors(mode);
  const [lineIndex, setLineIndex] = React.useState(0);
  const [charIndex, setCharIndex] = React.useState(0);
  const [started, setStarted] = React.useState(false);
  const [reduceMotion, setReduceMotion] = React.useState(false);

  React.useEffect(() => {
    setReduceMotion(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setStarted(true), 500);
    return () => window.clearTimeout(timer);
  }, []);

  React.useEffect(() => {
    if (!started || reduceMotion) return;

    if (lineIndex >= TERMINAL_LINES.length) {
      const reset = window.setTimeout(() => {
        setLineIndex(0);
        setCharIndex(0);
      }, 4500);
      return () => window.clearTimeout(reset);
    }

    const line = TERMINAL_LINES[lineIndex];
    if (charIndex < line.text.length) {
      const tick = window.setTimeout(() => setCharIndex((value) => value + 1), typingDelay(line, charIndex));
      return () => window.clearTimeout(tick);
    }

    const next = window.setTimeout(() => {
      setLineIndex((value) => value + 1);
      setCharIndex(0);
    }, pauseAfterLine(line));
    return () => window.clearTimeout(next);
  }, [started, lineIndex, charIndex, reduceMotion]);

  const prefixColor = (prefix: TerminalLine["prefix"]) => {
    if (prefix === "[User]") return USER_COLOR;
    if (prefix === "[Keprix]") return KEPRIX_COLOR;
    return colors.textSecondary;
  };

  const renderLine = (line: TerminalLine, visibleText: string, showCursor: boolean) => {
    const isChat = line.prefix === "[User]" || line.prefix === "[Keprix]";
    const color = prefixColor(line.prefix);

    if (isChat) {
      return (
        <Box key={`${line.prefix}-${line.text}`} sx={{ mb: 0.75 }}>
          <Typography
            component="div"
            sx={{ color, fontFamily: MARKETING_MONO_FONT, fontSize: "inherit", lineHeight: 1.6 }}
          >
            {line.prefix}
          </Typography>
          <Typography
            component="div"
            sx={{
              color: colors.textPrimary,
              fontFamily: MARKETING_MONO_FONT,
              fontSize: "inherit",
              lineHeight: 1.6,
              pl: 0.5,
            }}
          >
            {visibleText}
            {showCursor ? <TerminalCursor color={color} /> : null}
          </Typography>
        </Box>
      );
    }

    return (
      <Box key={`${line.prefix}-${line.text}`} sx={{ display: "flex", gap: 1, mb: 0.5, alignItems: "baseline" }}>
        <Typography
          component="span"
          sx={{ color, fontFamily: MARKETING_MONO_FONT, whiteSpace: "nowrap", fontSize: "inherit" }}
        >
          {line.prefix}
        </Typography>
        <Typography component="span" sx={{ color: colors.textPrimary, fontFamily: MARKETING_MONO_FONT, fontSize: "inherit" }}>
          {visibleText}
          {showCursor ? <TerminalCursor color={colors.textPrimary} /> : null}
        </Typography>
      </Box>
    );
  };

  const completedCount = reduceMotion ? TERMINAL_LINES.length : lineIndex;
  const activeLine = reduceMotion ? null : TERMINAL_LINES[lineIndex];
  const activeText = activeLine ? activeLine.text.slice(0, charIndex) : "";
  const showActiveCursor = Boolean(activeLine) && (charIndex < (activeLine?.text.length ?? 0) || lineIndex < TERMINAL_LINES.length);
  const finished = lineIndex >= TERMINAL_LINES.length;

  return (
    <Box
      role="img"
      aria-label="Keprix terminal demo showing Channel Shield workflow"
      sx={{
        bgcolor: mode === "dark" ? "rgba(10,12,20,0.85)" : alpha(colors.bgCard, 0.95),
        border: `1px solid ${alpha(colors.primary, 0.3)}`,
        borderRadius: 3,
        overflow: "hidden",
        fontFamily: MARKETING_MONO_FONT,
        fontSize: { xs: "0.75rem", sm: "0.85rem" },
        lineHeight: 1.7,
        backdropFilter: "blur(12px)",
        boxShadow: `0 0 60px ${alpha(colors.primary, 0.18)}, 0 24px 64px ${alpha("#000", mode === "dark" ? 0.6 : 0.12)}`,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1,
          bgcolor: alpha(mode === "dark" ? "#fff" : "#000", 0.04),
          borderBottom: `1px solid ${alpha(colors.divider, 0.5)}`,
          display: "flex",
          gap: 0.75,
          alignItems: "center",
        }}
      >
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <Box key={c} sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: c }} />
        ))}
        <Typography
          sx={{ ml: 1, fontSize: "0.7rem", color: colors.textSecondary, fontFamily: MARKETING_MONO_FONT }}
        >
          keprix - command center
        </Typography>
      </Box>

      <Box sx={{ p: { xs: 2, sm: 3 }, minHeight: { xs: 260, sm: 300 } }}>
        {TERMINAL_LINES.slice(0, completedCount).map((line) => renderLine(line, line.text, false))}
        {activeLine ? renderLine(activeLine, activeText, showActiveCursor && !finished) : null}
        {finished && !reduceMotion ? (
          <Box sx={{ mt: 0.5 }}>
            <TerminalCursor color={colors.textPrimary} />
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}

const STACK_ITEMS = [
  { name: "Anthropic", color: "#cc785c" },
  { name: "OpenAI", color: "#10a37f" },
  { name: "Gemini", color: "#4285f4" },
  { name: "Ollama", color: "#9b9b9b" },
  { name: "Groq", color: "#f55036" },
  { name: "Telegram", color: "#2aabee" },
  { name: "Discord", color: "#5865f2" },
  { name: "Docker", color: "#2496ed" },
] as const;

type StackItem = (typeof STACK_ITEMS)[number];

function StackPill({
  item,
  colors,
  isDark,
}: {
  item: StackItem;
  colors: ReturnType<typeof getMarketingColors>;
  isDark: boolean;
}) {
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 1,
        px: 2,
        py: 0.75,
        borderRadius: 999,
        flexShrink: 0,
        fontSize: "0.8rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        color: colors.textPrimary,
        bgcolor: isDark ? alpha("#fff", 0.06) : colors.bgCard,
        border: `1px solid ${isDark ? alpha("#fff", 0.14) : colors.divider}`,
        whiteSpace: "nowrap",
      }}
    >
      <Box
        aria-hidden
        sx={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          bgcolor: item.color,
          flexShrink: 0,
          boxShadow: `0 0 8px ${alpha(item.color, isDark ? 0.8 : 0.45)}`,
        }}
      />
      {item.name}
    </Box>
  );
}

function StackCarousel({
  colors,
  isDark,
}: {
  colors: ReturnType<typeof getMarketingColors>;
  isDark: boolean;
}) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const loopItems = React.useMemo(() => [...STACK_ITEMS, ...STACK_ITEMS], []);

  React.useEffect(() => {
    setReduceMotion(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  return (
    <Box
      sx={{
        position: "relative",
        flex: 1,
        minWidth: 0,
        py: 1,
        overflow: "hidden",
        maskImage: isDark
          ? "linear-gradient(to right, transparent 0%, #000 8%, #000 92%, transparent 100%)"
          : "linear-gradient(to right, transparent 0%, #000 6%, #000 94%, transparent 100%)",
        WebkitMaskImage: isDark
          ? "linear-gradient(to right, transparent 0%, #000 8%, #000 92%, transparent 100%)"
          : "linear-gradient(to right, transparent 0%, #000 6%, #000 94%, transparent 100%)",
      }}
    >
      <Box
        aria-label="Supported integrations"
        sx={{
          display: "flex",
          width: "max-content",
          gap: 1.25,
          animation: reduceMotion ? "none" : `${marqueeScroll} 32s linear infinite`,
          "@media (prefers-reduced-motion: reduce)": {
            animation: "none",
            flexWrap: "wrap",
            justifyContent: "center",
            width: "100%",
          },
          "&:hover": {
            animationPlayState: "paused",
          },
        }}
      >
        {(reduceMotion ? STACK_ITEMS : loopItems).map((item, index) => (
          <StackPill key={`${item.name}-${index}`} item={item} colors={colors} isDark={isDark} />
        ))}
      </Box>
    </Box>
  );
}

export function Hero() {
  const { mode } = useThemeMode();
  const colors = getMarketingColors(mode);
  const isDark = mode === "dark";

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
          bgcolor: colors.bgDefault,
          transition: "background-color 0.25s ease",
        }}
      >
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            inset: 0,
            zIndex: 0,
            pointerEvents: "none",
            background: isDark
              ? `
              radial-gradient(circle at 72% 35%, ${alpha(colors.primary, 0.28)} 0%, transparent 26%),
              radial-gradient(circle at 86% 58%, ${alpha(colors.secondary, 0.22)} 0%, transparent 25%),
              linear-gradient(135deg, ${colors.bgDefault} 0%, ${alpha(colors.bgPaper, 0.94)} 100%)
            `
              : `
              radial-gradient(circle at 76% 36%, ${alpha(colors.primary, 0.18)} 0%, transparent 28%),
              radial-gradient(circle at 88% 60%, ${alpha(colors.secondary, 0.14)} 0%, transparent 24%),
              linear-gradient(135deg, ${colors.bgDefault} 0%, ${alpha(colors.bgCard, 0.96)} 100%)
            `,
          }}
        />

        {/* Readability overlay: keep particles atmospheric, protect copy */}
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            inset: 0,
            zIndex: 0,
            background: isDark
              ? `
              radial-gradient(ellipse 80% 60% at 50% 20%, rgba(10,10,16,0.35) 0%, rgba(10,10,16,0.72) 70%),
              linear-gradient(to bottom, rgba(10,10,16,0.2) 0%, rgba(10,10,16,0.85) 100%)
            `
              : `
              linear-gradient(90deg, ${colors.bgDefault} 0%, ${alpha(colors.bgDefault, 0.97)} 32%, ${alpha(colors.bgDefault, 0.72)} 48%, ${alpha(colors.bgDefault, 0.28)} 68%, transparent 100%),
              linear-gradient(to bottom, ${alpha(colors.bgDefault, 0.2)} 0%, transparent 40%, ${alpha(colors.bgDefault, 0.35)} 100%),
              radial-gradient(ellipse 60% 55% at 82% 45%, ${alpha(colors.primary, 0.12)} 0%, transparent 72%)
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
            <Box
              sx={{
                position: "relative",
                ...(isDark
                  ? {}
                  : {
                      "&::before": {
                        content: '""',
                        position: "absolute",
                        inset: { xs: "-12px -16px", md: "-20px -28px" },
                        borderRadius: 3,
                        background: `linear-gradient(135deg, ${alpha(colors.bgDefault, 0.92)} 0%, ${alpha(colors.bgDefault, 0.78)} 70%, ${alpha(colors.bgDefault, 0.35)} 100%)`,
                        zIndex: -1,
                        pointerEvents: "none",
                      },
                    }),
              }}
            >
              <Box sx={{ mb: 3 }}>
                <KeprixLogo variant="full" size="lg" onDark={isDark} />
              </Box>
              <Chip
                label="Open source - MIT license"
                size="small"
                sx={{
                  mb: 2,
                  bgcolor: alpha(colors.primary, 0.12),
                  color: colors.primary,
                  border: `1px solid ${alpha(colors.primary, 0.3)}`,
                  fontWeight: 600,
                  fontSize: "0.75rem",
                }}
              />
              <Typography
                component="p"
                sx={{
                  fontSize: { xs: "0.9rem", md: "0.98rem" },
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: alpha(colors.primary, 0.95),
                  mb: 1.5,
                }}
              >
                Self-hosted. Soft Wall. User approve.
              </Typography>
              <Typography
                component="h1"
                sx={{
                  fontFamily: MARKETING_DISPLAY_FONT,
                  fontSize: { xs: "3rem", sm: "3.85rem", md: "4.4rem", lg: "4.9rem" },
                  fontWeight: 700,
                  lineHeight: 0.98,
                  letterSpacing: "-0.03em",
                  color: colors.textPrimary,
                  mb: 2,
                }}
              >
                The AI agent
                <Box
                  component="span"
                  sx={{ display: "block", color: colors.primary }}
                >
                  that creates the tools it needs.
                </Box>
              </Typography>
              <Typography
                sx={{
                  fontSize: { xs: "1rem", md: "1.0625rem" },
                  color: alpha(colors.textPrimary, 0.9),
                  lineHeight: 1.8,
                  mb: 4,
                  maxWidth: 560,
                }}
              >
                Propose tools, protect channels, run CRM, and embed via sidecar; Keprix tests
                changes and waits for your approval before anything goes live.
              </Typography>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Button
                  component={Link}
                  href="/download"
                  variant="contained"
                  size="large"
                  sx={{
                    fontWeight: 700,
                    px: 3.5,
                    borderRadius: "9999px",
                    background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`,
                    boxShadow: `0 4px 24px ${alpha(colors.primary, 0.4)}`,
                    "&:hover": {
                      boxShadow: `0 6px 32px ${alpha(colors.primary, 0.55)}`,
                    },
                  }}
                >
                  Install Community
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
                    borderColor: alpha(colors.divider, 0.6),
                    color: colors.textSecondary,
                    "&:hover": {
                      borderColor: colors.primary,
                      color: colors.textPrimary,
                      bgcolor: alpha(colors.primary, 0.06),
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
                  background: `radial-gradient(ellipse at center, ${alpha(colors.primary, 0.1)} 0%, transparent 70%)`,
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
            background: `linear-gradient(to bottom, transparent 0%, ${colors.bgDefault} 100%)`,
            pointerEvents: "none",
          }}
        />
      </Box>

      {/* Infinite logo slider section */}
      <Box
        component="section"
        sx={{
          bgcolor: colors.bgDefault,
          py: 4,
          borderBottom: `1px solid ${alpha(colors.divider, isDark ? 0.4 : 1)}`,
          transition: "background-color 0.25s ease",
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
                borderRight: { md: `1px solid ${alpha(colors.divider, isDark ? 0.4 : 1)}` },
                minWidth: { md: 160 },
              }}
            >
              <Typography
                sx={{
                  fontSize: "0.75rem",
                  color: colors.textSecondary,
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

            <StackCarousel colors={colors} isDark={isDark} />
          </Box>
        </Container>
      </Box>
    </>
  );
}

"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import { alpha, keyframes } from "@mui/material/styles";
import * as React from "react";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { KeprixLogo } from "@/components/shared/KeprixLogo";
import {
  getMarketingColors,
  MARKETING_BTN_RADIUS,
  MARKETING_DISPLAY_FONT,
  MARKETING_MONO_FONT,
} from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const blink = keyframes`
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
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

const INSTALL_CMD =
  "curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash";

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
    const timer = window.setTimeout(() => setStarted(true), 400);
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
    if (prefix === "[User]") return colors.textSecondary;
    if (prefix === "[Keprix]") return colors.primary;
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
            sx={{ color, fontFamily: MARKETING_MONO_FONT, fontSize: "inherit", lineHeight: 1.55 }}
          >
            {line.prefix}
          </Typography>
          <Typography
            component="div"
            sx={{
              color: colors.textPrimary,
              fontFamily: MARKETING_MONO_FONT,
              fontSize: "inherit",
              lineHeight: 1.55,
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
        <Typography
          component="span"
          sx={{ color: colors.textPrimary, fontFamily: MARKETING_MONO_FONT, fontSize: "inherit" }}
        >
          {visibleText}
          {showCursor ? <TerminalCursor color={colors.textPrimary} /> : null}
        </Typography>
      </Box>
    );
  };

  const completedCount = reduceMotion ? TERMINAL_LINES.length : lineIndex;
  const activeLine = reduceMotion ? null : TERMINAL_LINES[lineIndex];
  const activeText = activeLine ? activeLine.text.slice(0, charIndex) : "";
  const showActiveCursor =
    Boolean(activeLine) && (charIndex < (activeLine?.text.length ?? 0) || lineIndex < TERMINAL_LINES.length);
  const finished = lineIndex >= TERMINAL_LINES.length;

  return (
    <Box
      role="img"
      aria-label="Keprix terminal demo showing Channel Shield workflow"
      sx={{
        bgcolor: colors.bgPaper,
        border: `1px solid ${colors.divider}`,
        borderRadius: "8px",
        overflow: "hidden",
        fontFamily: MARKETING_MONO_FONT,
        fontSize: { xs: "0.75rem", sm: "0.82rem" },
        lineHeight: 1.65,
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1,
          borderBottom: `1px solid ${colors.divider}`,
          display: "flex",
          gap: 0.75,
          alignItems: "center",
        }}
      >
        {["#78716C", "#78716C", "#78716C"].map((c, i) => (
          <Box key={i} sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: c, opacity: 0.55 }} />
        ))}
        <Typography
          sx={{ ml: 1, fontSize: "0.68rem", color: colors.textSecondary, fontFamily: MARKETING_MONO_FONT }}
        >
          keprix - command center
        </Typography>
      </Box>

      <Box sx={{ p: { xs: 2, sm: 2.5 }, minHeight: { xs: 260, sm: 300 } }}>
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
  "Anthropic",
  "OpenAI",
  "Gemini",
  "Ollama",
  "Groq",
  "Telegram",
  "Discord",
  "Docker",
] as const;

export function Hero() {
  const { mode } = useThemeMode();
  const colors = getMarketingColors(mode);
  const isDark = mode === "dark";
  const [copiedInstall, setCopiedInstall] = React.useState(false);

  const handleCopyInstall = async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(INSTALL_CMD);
        setCopiedInstall(true);
        window.setTimeout(() => setCopiedInstall(false), 2000);
      }
    } catch {
      // ignore
    }
  };

  const scrollToInstall = (e: React.MouseEvent) => {
    const el = document.getElementById("install");
    if (el) {
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth" });
      window.history.pushState(null, "", "#install");
    }
  };

  return (
    <>
      <Box
        component="section"
        sx={{
          position: "relative",
          overflow: "hidden",
          minHeight: { xs: "100vh", md: "92vh" },
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          bgcolor: colors.bgDefault,
          backgroundImage: isDark
            ? `linear-gradient(${alpha("#fff", 0.03)} 1px, transparent 1px), linear-gradient(90deg, ${alpha("#fff", 0.03)} 1px, transparent 1px)`
            : `linear-gradient(${alpha("#000", 0.04)} 1px, transparent 1px), linear-gradient(90deg, ${alpha("#000", 0.04)} 1px, transparent 1px)`,
          backgroundSize: "48px 48px",
          backgroundPosition: "center top",
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            position: "relative",
            zIndex: 1,
            pt: { xs: 14, md: 18 },
            pb: { xs: 8, md: 12 },
          }}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.05fr) minmax(0, 0.95fr)" },
              gap: { xs: 5, lg: 7 },
              alignItems: "center",
            }}
          >
            <Box>
              <Box sx={{ mb: 3 }}>
                <KeprixLogo variant="full" size="lg" onDark={isDark} />
              </Box>

              <Typography
                component="h1"
                sx={{
                  fontFamily: MARKETING_DISPLAY_FONT,
                  fontSize: { xs: "2.6rem", sm: "3.25rem", md: "3.75rem" },
                  fontWeight: 600,
                  lineHeight: 1.08,
                  letterSpacing: "-0.03em",
                  color: colors.textPrimary,
                  mb: 2.5,
                  maxWidth: 560,
                }}
              >
                Self-hosted agent OS that proposes tools, then waits for you.
              </Typography>

              <Typography
                sx={{
                  fontSize: { xs: "1.02rem", md: "1.08rem" },
                  color: colors.textSecondary,
                  lineHeight: 1.65,
                  mb: 3.5,
                  maxWidth: 480,
                }}
              >
                Channel Shield, Soft Wall, CRM, memory, and reviewable self-coding on your
                infrastructure. MIT licensed. No shared keys.
              </Typography>

              <Box sx={{ display: "flex", alignItems: "center", gap: 2.5, flexWrap: "wrap", mb: 3 }}>
                <Button
                  component="a"
                  href="#install"
                  variant="contained"
                  size="large"
                  onClick={scrollToInstall}
                  sx={{
                    fontWeight: 600,
                    px: 2.75,
                    py: 1.15,
                    borderRadius: MARKETING_BTN_RADIUS,
                    bgcolor: colors.primary,
                    color: isDark ? "#0C0C0B" : "#FAFAF9",
                    boxShadow: "none",
                    textTransform: "none",
                    "&:hover": {
                      bgcolor: colors.primary,
                      filter: "brightness(1.06)",
                      boxShadow: "none",
                    },
                  }}
                >
                  Install on your machine
                </Button>
                <Button
                  component="a"
                  href="https://github.com/malike2356/keprix"
                  target="_blank"
                  rel="noopener noreferrer"
                  endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
                  sx={{
                    fontWeight: 500,
                    px: 0.5,
                    color: colors.textSecondary,
                    textTransform: "none",
                    minWidth: 0,
                    "&:hover": {
                      bgcolor: "transparent",
                      color: colors.textPrimary,
                    },
                  }}
                >
                  View source
                </Button>
              </Box>

              <Box
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  maxWidth: "100%",
                  bgcolor: colors.bgPaper,
                  border: `1px solid ${colors.divider}`,
                  borderRadius: MARKETING_BTN_RADIUS,
                  p: 0.5,
                  pl: 1.5,
                }}
              >
                <Typography
                  component="span"
                  sx={{
                    color: colors.primary,
                    fontFamily: MARKETING_MONO_FONT,
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    mr: 1,
                    userSelect: "none",
                  }}
                >
                  $
                </Typography>
                <Typography
                  component="code"
                  sx={{
                    fontFamily: MARKETING_MONO_FONT,
                    fontSize: { xs: "0.7rem", sm: "0.78rem" },
                    color: colors.textPrimary,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    mr: 1,
                  }}
                >
                  {INSTALL_CMD}
                </Typography>
                <Tooltip title={copiedInstall ? "Copied" : "Copy install command"}>
                  <IconButton
                    onClick={handleCopyInstall}
                    size="small"
                    sx={{
                      color: copiedInstall ? colors.primary : colors.textSecondary,
                      borderRadius: "4px",
                      "&:hover": { bgcolor: alpha(colors.primary, 0.08) },
                    }}
                    aria-label="Copy install command"
                  >
                    {copiedInstall ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              </Box>

              <Typography
                sx={{
                  mt: 1.25,
                  fontSize: "0.75rem",
                  color: colors.textSecondary,
                }}
              >
                Linux, macOS, WSL2. Deploy in about two minutes.
              </Typography>
            </Box>

            <Box>
              <TerminalWindow />
            </Box>
          </Box>
        </Container>
      </Box>

      <Box
        component="section"
        sx={{
          bgcolor: colors.bgDefault,
          py: 3.5,
          borderTop: `1px solid ${colors.divider}`,
          borderBottom: `1px solid ${colors.divider}`,
        }}
      >
        <Container maxWidth="lg">
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              alignItems: { xs: "flex-start", md: "center" },
              gap: { xs: 2, md: 4 },
            }}
          >
            <Typography
              sx={{
                flexShrink: 0,
                fontSize: "0.72rem",
                color: colors.textSecondary,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                fontWeight: 600,
                minWidth: { md: 110 },
              }}
            >
              Works with
            </Typography>
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap: { xs: 1.5, md: 2.5 },
                rowGap: 1,
              }}
            >
              {STACK_ITEMS.map((name) => (
                <Typography
                  key={name}
                  sx={{
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: colors.textPrimary,
                    opacity: 0.78,
                  }}
                >
                  {name}
                </Typography>
              ))}
            </Box>
          </Box>
        </Container>
      </Box>
    </>
  );
}

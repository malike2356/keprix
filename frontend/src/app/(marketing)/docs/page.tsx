"use client";

import dynamic from "next/dynamic";
import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { alpha } from "@mui/material/styles";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import TuneIcon from "@mui/icons-material/Tune";
import SpaceDashboardIcon from "@mui/icons-material/SpaceDashboard";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import ShieldIcon from "@mui/icons-material/Shield";
import ApiIcon from "@mui/icons-material/Api";
import StorageIcon from "@mui/icons-material/Storage";
import GroupsIcon from "@mui/icons-material/Groups";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { getMarketingColors } from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";
import {
  DOCS_GITHUB_EDIT_URL,
  DOCS_SECTIONS,
} from "@/lib/docs-catalog";
import { DOCS_QUICKSTART_URL, docsPageUrl, isExternalDocsUrl } from "@/lib/docs-url";

const DottedSurfaceBackground = dynamic(
  () => import("@/components/ui/dotted-surface-background").then((mod) => mod.DottedSurfaceBackground),
  { ssr: false },
);

const INSTALL_CMD = `git clone https://github.com/malike2356/keprix.git && cd keprix
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d --build`;

const SECTION_META: Record<string, { icon: React.ElementType; color: string; accent: string }> = {
  "Getting started": { icon: RocketLaunchIcon, color: "#10B981", accent: "rgba(16,185,129,0.12)" },
  "Configuration":   { icon: TuneIcon,          color: "#6495ed", accent: "rgba(100,149,237,0.12)" },
  "Workspace":       { icon: SpaceDashboardIcon, color: "#6c5ce7", accent: "rgba(108,92,231,0.12)" },
  "Apps and research": { icon: TravelExploreIcon, color: "#F59E0B", accent: "rgba(245,158,11,0.12)" },
  "Automations":     { icon: AutoFixHighIcon,    color: "#ef4444", accent: "rgba(239,68,68,0.12)" },
  "Security and admin": { icon: ShieldIcon,      color: "#64748b", accent: "rgba(100,116,139,0.12)" },
  "Integrations and reference": { icon: ApiIcon, color: "#06b6d4", accent: "rgba(6,182,212,0.12)" },
  "Operations": { icon: StorageIcon, color: "#84cc16", accent: "rgba(132,204,22,0.12)" },
  "Community": { icon: GroupsIcon, color: "#ec4899", accent: "rgba(236,72,153,0.12)" },
};

const QUICK_LINKS = [
  { label: "Quickstart (Docker)", href: DOCS_QUICKSTART_URL },
  { label: "Environment variables", href: docsPageUrl("configuration/environment-variables") },
  { label: "LLM providers", href: docsPageUrl("configuration/llm-providers") },
  { label: "Mutation engine", href: docsPageUrl("features/agent") },
  { label: "SDK reference", href: docsPageUrl("integrations/sdk") },
  { label: "REST API", href: docsPageUrl("reference/api") },
] as const;

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <Box
      component="button"
      onClick={async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      aria-label="Copy install commands"
      sx={{
        position: "absolute",
        top: 14,
        right: 14,
        bgcolor: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 1,
        p: 0.75,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "rgba(255,255,255,0.55)",
        transition: "all 0.15s",
        "&:hover": { bgcolor: "rgba(255,255,255,0.1)", color: "#fff" },
      }}
    >
      {copied ? <CheckIcon sx={{ fontSize: 16, color: "#10B981" }} /> : <ContentCopyIcon sx={{ fontSize: 16 }} />}
    </Box>
  );
}

export default function DocsPage() {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const isDark = mode === "dark";

  return (
    <Box sx={{ bgcolor: c.bgDefault, minHeight: "100vh", position: "relative", transition: "background-color 0.25s ease" }}>
      <DottedSurfaceBackground fixed mode={isDark ? "dark" : "light"} />

      <Box
        aria-hidden
        sx={{
          position: "fixed",
          inset: 0,
          zIndex: 0,
          pointerEvents: "none",
          background: isDark
            ? `
            radial-gradient(ellipse at 50% 35%, ${alpha(c.primary, 0.08)} 0%, transparent 45%),
            radial-gradient(ellipse at 50% 100%, rgba(8, 8, 15, 0.35) 0%, transparent 65%)
          `
            : `
            radial-gradient(ellipse at 50% 0%, ${alpha(c.primary, 0.1)} 0%, transparent 45%),
            radial-gradient(ellipse at 80% 100%, ${alpha(c.secondary, 0.08)} 0%, transparent 50%)
          `,
        }}
      />

      <Box sx={{ position: "relative", zIndex: 1 }}>

      {/* Hero */}
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          pt: { xs: 12, md: 18 },
          pb: { xs: 8, md: 12 },
          textAlign: "center",
        }}
      >
        {/* Background glows */}
        <Box aria-hidden sx={{ position: "absolute", top: -200, left: "50%", transform: "translateX(-50%)", width: 800, height: 600, borderRadius: "50%", background: "radial-gradient(ellipse at center, rgba(108,92,231,0.14) 0%, transparent 70%)", filter: "blur(48px)", pointerEvents: "none" }} />
        <Box aria-hidden sx={{ position: "absolute", top: "30%", left: "20%", width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, rgba(100,149,237,0.07) 0%, transparent 70%)", filter: "blur(40px)", pointerEvents: "none" }} />
        <Box aria-hidden sx={{ position: "absolute", top: "20%", right: "15%", width: 280, height: 280, borderRadius: "50%", background: "radial-gradient(circle, rgba(16,185,129,0.06) 0%, transparent 70%)", filter: "blur(36px)", pointerEvents: "none" }} />

        <Container maxWidth="lg" sx={{ position: "relative" }}>
          {/* Version badge */}
          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 0.75,
              px: 1.75,
              py: 0.6,
              mb: 3,
              borderRadius: 5,
              border: "1px solid rgba(108,92,231,0.3)",
              bgcolor: "rgba(108,92,231,0.08)",
            }}
          >
            <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "#10B981", boxShadow: "0 0 8px #10B981" }} />
            <Typography sx={{ fontSize: "0.75rem", fontWeight: 700, color: "#6c5ce7", letterSpacing: "0.06em" }}>
              Keprix - Open Source Docs
            </Typography>
          </Box>

          <Typography
            component="h1"
            sx={{
              fontSize: { xs: "2.5rem", md: "4rem" },
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.05,
              mb: 2.5,
              background: "linear-gradient(140deg, #ededf8 20%, rgba(108,92,231,0.85) 70%, #6495ed 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Build with Keprix.
            <br />
            Ship faster.
          </Typography>

          <Typography
            sx={{
              color: "#8888a8",
              fontSize: { xs: "1rem", md: "1.2rem" },
              lineHeight: 1.7,
              maxWidth: 520,
              mx: "auto",
              mb: 5,
            }}
          >
            Complete operator and developer reference: workspace, automations, security, integrations, and auto-generated API reference.
          </Typography>

          {/* Primary actions */}
          <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap", mb: 8 }}>
            <Button
              component="a"
              href={DOCS_QUICKSTART_URL}
              target={isExternalDocsUrl(DOCS_QUICKSTART_URL) ? "_blank" : undefined}
              rel={isExternalDocsUrl(DOCS_QUICKSTART_URL) ? "noopener noreferrer" : undefined}
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              sx={{
                fontWeight: 700,
                px: 4,
                borderRadius: "9999px",
                background: "linear-gradient(135deg, #6c5ce7 0%, #6495ed 100%)",
                boxShadow: "0 4px 28px rgba(108,92,231,0.45)",
                "&:hover": { boxShadow: "0 6px 36px rgba(108,92,231,0.6)" },
              }}
            >
              Get started
            </Button>
            <Button
              component="a"
              href={docsPageUrl("reference/api")}
              target={isExternalDocsUrl(docsPageUrl("reference/api")) ? "_blank" : undefined}
              rel={isExternalDocsUrl(docsPageUrl("reference/api")) ? "noopener noreferrer" : undefined}
              variant="outlined"
              size="large"
              endIcon={<ApiIcon />}
              sx={{
                fontWeight: 600,
                px: 4,
                borderRadius: "9999px",
                borderColor: "rgba(255,255,255,0.12)",
                color: "#8888a8",
                "&:hover": { borderColor: "rgba(108,92,231,0.5)", color: "#ededf8", bgcolor: "rgba(108,92,231,0.06)" },
              }}
            >
              API explorer
            </Button>
            <Button
              component="a"
              href={DOCS_GITHUB_EDIT_URL}
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              size="large"
              endIcon={<OpenInNewIcon sx={{ fontSize: "0.85rem !important" }} />}
              sx={{
                fontWeight: 600,
                px: 3.5,
                borderRadius: "9999px",
                borderColor: "rgba(255,255,255,0.08)",
                color: "#8888a8",
                "&:hover": { borderColor: "rgba(255,255,255,0.2)", color: "#ededf8", bgcolor: "rgba(255,255,255,0.04)" },
              }}
            >
              Edit on GitHub
            </Button>
          </Box>

          {/* Quick-access pills */}
          <Box
            sx={{
              display: "flex",
              gap: 1.25,
              justifyContent: "center",
              flexWrap: "wrap",
              maxWidth: 700,
              mx: "auto",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: alpha(c.textSecondary, 0.5), mr: 0.5, alignSelf: "center", letterSpacing: "0.06em", textTransform: "uppercase", fontWeight: 700 }}>
              Popular:
            </Typography>
            {QUICK_LINKS.map((ql) => (
              <Box
                key={ql.label}
                component={isExternalDocsUrl(ql.href) ? "a" : Link}
                href={ql.href}
                {...(isExternalDocsUrl(ql.href) ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                sx={{
                  px: 2,
                  py: 0.6,
                  borderRadius: 5,
                  border: "1px solid rgba(255,255,255,0.07)",
                  bgcolor: "rgba(255,255,255,0.03)",
                  color: "#8888a8",
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  textDecoration: "none",
                  transition: "all 0.15s",
                  "&:hover": {
                    borderColor: "rgba(108,92,231,0.3)",
                    color: "#ededf8",
                    bgcolor: "rgba(108,92,231,0.08)",
                  },
                }}
              >
                {ql.label}
              </Box>
            ))}
          </Box>
        </Container>
      </Box>

      {/* Section grid */}
      <Container maxWidth="lg" sx={{ pb: { xs: 10, md: 14 } }}>

        {/* Divider */}
        <Box sx={{ height: 1, bgcolor: "rgba(255,255,255,0.05)", mb: 8 }} />

        <Typography
          sx={{
            fontSize: "0.75rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: alpha(c.textSecondary, 0.5),
            mb: 4,
          }}
        >
          Browse by category
        </Typography>

        <Grid container spacing={2.5}>
          {DOCS_SECTIONS.map((section) => {
            const meta = SECTION_META[section.title] ?? {
              icon: ApiIcon,
              color: "#6c5ce7",
              accent: "rgba(108,92,231,0.1)",
            };
            const Icon = meta.icon;
            const firstHref = section.items[0]?.href ?? "#";
            const external = isExternalDocsUrl(firstHref);

            return (
              <Grid key={section.title} size={{ xs: 12, sm: 6, lg: 4 }}>
                <Box
                  component={external ? "a" : Link}
                  href={firstHref}
                  {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  sx={{
                    display: "block",
                    height: "100%",
                    textDecoration: "none",
                    borderRadius: 2.5,
                    border: "1px solid rgba(255,255,255,0.07)",
                    bgcolor: "rgba(10,10,22,0.65)",
                    backdropFilter: "blur(16px)",
                    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 4px 20px rgba(0,0,0,0.3)",
                    p: 3,
                    position: "relative",
                    overflow: "hidden",
                    transition: "border-color 0.22s, box-shadow 0.22s, transform 0.22s",
                    "&:hover": {
                      borderColor: alpha(meta.color, 0.35),
                      boxShadow: `0 8px 36px rgba(0,0,0,0.4), 0 0 0 1px ${alpha(meta.color, 0.12)}, inset 0 1px 0 rgba(255,255,255,0.08)`,
                      transform: "translateY(-2px)",
                      "& .section-arrow": { opacity: 1, transform: "translateX(2px)" },
                    },
                  }}
                >
                  {/* Specular */}
                  <Box aria-hidden sx={{ position: "absolute", top: 0, left: 0, right: 0, height: "45%", background: "linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%)", pointerEvents: "none", borderRadius: "10px 10px 0 0" }} />

                  {/* Icon */}
                  <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 2.5 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: 2,
                        bgcolor: meta.accent,
                        border: `1px solid ${alpha(meta.color, 0.22)}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <Icon sx={{ color: meta.color, fontSize: 22 }} />
                    </Box>

                    {/* Item count badge */}
                    <Box
                      sx={{
                        px: 1.25,
                        py: 0.4,
                        borderRadius: 5,
                        border: "1px solid rgba(255,255,255,0.07)",
                        bgcolor: "rgba(255,255,255,0.04)",
                      }}
                    >
                      <Typography sx={{ fontSize: "0.72rem", fontWeight: 600, color: alpha(c.textSecondary, 0.6) }}>
                        {section.items.length} articles
                      </Typography>
                    </Box>
                  </Box>

                  <Typography
                    sx={{
                      fontWeight: 700,
                      fontSize: "1rem",
                      letterSpacing: "-0.01em",
                      color: c.textPrimary,
                      mb: 0.75,
                    }}
                  >
                    {section.title}
                  </Typography>
                  <Typography
                    sx={{ fontSize: "0.85rem", color: c.textSecondary, lineHeight: 1.6, mb: 2.5 }}
                  >
                    {section.description}
                  </Typography>

                  {/* Preview items */}
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
                    {section.items.slice(0, 3).map((item) => (
                      <Typography
                        key={item.href}
                        sx={{
                          fontSize: "0.8rem",
                          color: alpha(c.textSecondary, 0.7),
                          "&::before": { content: '"- "', color: alpha(meta.color, 0.6) },
                        }}
                      >
                        {item.title}
                      </Typography>
                    ))}
                    {section.items.length > 3 && (
                      <Typography sx={{ fontSize: "0.78rem", color: alpha(meta.color, 0.7), fontWeight: 600, mt: 0.25 }}>
                        + {section.items.length - 3} more
                      </Typography>
                    )}
                  </Box>

                  {/* Arrow */}
                  <ArrowForwardIcon
                    className="section-arrow"
                    sx={{
                      position: "absolute",
                      bottom: 16,
                      right: 16,
                      fontSize: 16,
                      color: alpha(meta.color, 0.5),
                      opacity: 0,
                      transition: "opacity 0.2s, transform 0.2s",
                    }}
                  />
                </Box>
              </Grid>
            );
          })}
        </Grid>

        {/* Install strip */}
        <Box sx={{ mt: 8, height: 1, bgcolor: "rgba(255,255,255,0.05)", mb: 8 }} />

        <Box
          sx={{
            borderRadius: 3,
            overflow: "hidden",
            border: "1px solid rgba(255,255,255,0.07)",
            display: { xs: "block", lg: "grid" },
            gridTemplateColumns: "1fr 1fr",
          }}
        >
          {/* Left: headline */}
          <Box
            sx={{
              p: { xs: 4, md: 5 },
              bgcolor: "rgba(8,8,20,0.8)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              borderRight: { lg: "1px solid rgba(255,255,255,0.07)" },
              borderBottom: { xs: "1px solid rgba(255,255,255,0.07)", lg: "none" },
              position: "relative",
              overflow: "hidden",
            }}
          >
            <Box aria-hidden sx={{ position: "absolute", top: -80, left: -80, width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, rgba(108,92,231,0.1) 0%, transparent 70%)", filter: "blur(32px)", pointerEvents: "none" }} />
            <Typography
              component="p"
              sx={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#6c5ce7", mb: 1.5 }}
            >
              Deploy
            </Typography>
            <Typography
              component="h2"
              sx={{
                fontSize: { xs: "1.5rem", md: "2rem" },
                fontWeight: 800,
                letterSpacing: "-0.03em",
                lineHeight: 1.2,
                mb: 1.5,
                background: "linear-gradient(140deg, #ededf8 30%, rgba(108,92,231,0.85) 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                position: "relative",
              }}
            >
              Up and running in five minutes.
            </Typography>
            <Typography sx={{ color: "#8888a8", fontSize: "0.9rem", lineHeight: 1.7, mb: 3, position: "relative" }}>
              Three commands, Docker required. MIT licensed. No account.
            </Typography>
            <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap", position: "relative" }}>
              <Button
                component={Link}
                href="/auth/setup"
                variant="contained"
                sx={{
                  fontWeight: 700,
                  px: 3,
                  borderRadius: "9999px",
                  background: "linear-gradient(135deg, #6c5ce7 0%, #6495ed 100%)",
                  boxShadow: "0 4px 20px rgba(108,92,231,0.4)",
                  "&:hover": { boxShadow: "0 6px 28px rgba(108,92,231,0.55)" },
                }}
              >
                Deploy instance
              </Button>
              <Button
                component="a"
                href={DOCS_QUICKSTART_URL}
                target={isExternalDocsUrl(DOCS_QUICKSTART_URL) ? "_blank" : undefined}
                rel={isExternalDocsUrl(DOCS_QUICKSTART_URL) ? "noopener noreferrer" : undefined}
                variant="outlined"
                sx={{
                  fontWeight: 600,
                  px: 3,
                  borderRadius: "9999px",
                  borderColor: "rgba(255,255,255,0.12)",
                  color: "#8888a8",
                  "&:hover": { borderColor: "rgba(108,92,231,0.4)", color: "#ededf8", bgcolor: "rgba(108,92,231,0.06)" },
                }}
              >
                Read quickstart
              </Button>
            </Box>
          </Box>

          {/* Right: code block */}
          <Box
            sx={{
              p: { xs: 3, md: 4 },
              bgcolor: "#06060e",
              position: "relative",
              fontFamily: "monospace",
            }}
          >
            <Typography sx={{ fontSize: "0.72rem", color: alpha("#8888a8", 0.6), mb: 2, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Quick install
            </Typography>
            <Box
              component="pre"
              sx={{
                m: 0,
                fontFamily: "monospace",
                fontSize: "0.78rem",
                color: "#c9d1d9",
                overflow: "auto",
                whiteSpace: "pre-wrap",
                lineHeight: 2,
              }}
            >
              {INSTALL_CMD.split("\n").map((line, i) => (
                <Box key={i} component="div" sx={{ display: "flex", gap: 1.5 }}>
                  <Box component="span" sx={{ color: "rgba(108,92,231,0.6)", userSelect: "none", flexShrink: 0 }}>$</Box>
                  <Box component="span">{line.replace(/^\$ /, "")}</Box>
                </Box>
              ))}
            </Box>
            <CopyButton code={INSTALL_CMD} />
          </Box>
        </Box>
      </Container>
      </Box>
    </Box>
  );
}

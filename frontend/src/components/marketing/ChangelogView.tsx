"use client";

import dynamic from "next/dynamic";
import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import GitHubIcon from "@mui/icons-material/GitHub";
import HistoryIcon from "@mui/icons-material/History";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import SecurityIcon from "@mui/icons-material/Security";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { alpha } from "@mui/material/styles";
import type { ChangelogRelease } from "@/lib/changelog";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { getMarketingColors } from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const DottedSurfaceBackground = dynamic(
  () => import("@/components/ui/dotted-surface-background").then((mod) => mod.DottedSurfaceBackground),
  { ssr: false },
);

const CATEGORY_META: Record<string, { icon: React.ElementType; color: string }> = {
  Added: { icon: AddCircleOutlineIcon, color: "#10B981" },
  Changed: { icon: EditOutlinedIcon, color: "#6495ed" },
  Fixed: { icon: AutoFixHighIcon, color: "#6c5ce7" },
  Removed: { icon: DeleteOutlineIcon, color: "#EF4444" },
  Deprecated: { icon: WarningAmberIcon, color: "#F59E0B" },
  Security: { icon: SecurityIcon, color: "#6495ed" },
};

function formatDate(date: string): string {
  const parsed = new Date(`${date}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function releaseItemCount(release: ChangelogRelease): number {
  return release.sections.reduce((sum, section) => sum + section.items.length, 0);
}

type ChangelogViewProps = {
  releases: ChangelogRelease[];
};

export function ChangelogView({ releases }: ChangelogViewProps) {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const isDark = mode === "dark";
  const shipped = releases.filter((r) => !r.isUnreleased);
  const latest = shipped[0];
  const totalChanges = releases.reduce((sum, r) => sum + releaseItemCount(r), 0);

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
            radial-gradient(ellipse at 50% 20%, ${alpha(c.primary, 0.1)} 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, ${alpha(c.secondary, 0.06)} 0%, transparent 40%),
            radial-gradient(ellipse at 50% 100%, rgba(8, 8, 15, 0.4) 0%, transparent 65%)
          `
            : `
            radial-gradient(ellipse at 50% 0%, ${alpha(c.primary, 0.1)} 0%, transparent 45%),
            radial-gradient(ellipse at 90% 80%, ${alpha(c.secondary, 0.08)} 0%, transparent 40%)
          `,
        }}
      />

      <Box sx={{ position: "relative", zIndex: 1 }}>
        {/* Hero */}
        <Box
          sx={{
            pt: { xs: 14, md: 18 },
            pb: { xs: 6, md: 8 },
            textAlign: "center",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <Container maxWidth="md">
            <ScrollReveal>
              <Chip
                icon={<HistoryIcon sx={{ fontSize: "0.9rem !important" }} />}
                label="Release history"
                size="small"
                sx={{
                  mb: 3,
                  bgcolor: alpha(c.primary, 0.1),
                  color: c.primary,
                  border: `1px solid ${alpha(c.primary, 0.28)}`,
                  fontWeight: 600,
                  "& .MuiChip-icon": { color: c.primary },
                }}
              />
              <Typography
                component="h1"
                sx={{
                  fontSize: { xs: "2.5rem", md: "3.5rem" },
                  fontWeight: 900,
                  letterSpacing: "-0.04em",
                  lineHeight: 1.08,
                  mb: 2,
                  background: `linear-gradient(140deg, ${c.textPrimary} 25%, ${alpha(c.primary, 0.9)} 75%, ${c.secondary} 100%)`,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                What shipped, and what&apos;s next.
              </Typography>
              <Typography
                sx={{
                  color: c.textSecondary,
                  fontSize: { xs: "1rem", md: "1.1rem" },
                  lineHeight: 1.75,
                  maxWidth: 520,
                  mx: "auto",
                  mb: 4,
                }}
              >
                Parsed from{" "}
                <Box
                  component="a"
                  href="https://github.com/malike2356/keprix/blob/main/CHANGELOG.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ color: c.primary, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
                >
                  CHANGELOG.md
                </Box>
                . Every merge tagged here.
              </Typography>

              <Box sx={{ display: "flex", gap: 1.5, justifyContent: "center", flexWrap: "wrap" }}>
                <Chip
                  label={latest ? `Latest: v${latest.version}` : "No releases yet"}
                  sx={{
                    bgcolor: alpha(c.bgPaper, 0.6),
                    border: `1px solid ${alpha(c.divider, 0.5)}`,
                    color: c.textPrimary,
                    fontWeight: 600,
                  }}
                />
                <Chip
                  label={`${shipped.length} release${shipped.length === 1 ? "" : "s"}`}
                  sx={{
                    bgcolor: alpha(c.bgPaper, 0.6),
                    border: `1px solid ${alpha(c.divider, 0.5)}`,
                    color: c.textSecondary,
                    fontWeight: 500,
                  }}
                />
                <Chip
                  label={`${totalChanges} documented changes`}
                  sx={{
                    bgcolor: alpha(c.bgPaper, 0.6),
                    border: `1px solid ${alpha(c.divider, 0.5)}`,
                    color: c.textSecondary,
                    fontWeight: 500,
                  }}
                />
              </Box>
            </ScrollReveal>
          </Container>
        </Box>

        {/* Timeline */}
        <Container maxWidth="md" sx={{ pb: { xs: 10, md: 14 } }}>
          <Box sx={{ position: "relative" }}>
            {/* Vertical spine */}
            <Box
              aria-hidden
              sx={{
                position: "absolute",
                left: { xs: 15, md: 23 },
                top: 24,
                bottom: 24,
                width: 2,
                background: `linear-gradient(180deg, ${alpha(c.primary, 0.5)} 0%, ${alpha(c.divider, 0.3)} 50%, transparent 100%)`,
                borderRadius: 1,
              }}
            />

            <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {releases.map((release, index) => {
                const items = releaseItemCount(release);
                const isLatest = !release.isUnreleased && release === latest;

                return (
                  <ScrollReveal key={release.version} delay={index * 0.06}>
                    <Box sx={{ display: "flex", gap: { xs: 2, md: 3 }, alignItems: "flex-start" }}>
                      {/* Timeline node */}
                      <Box
                        sx={{
                          flexShrink: 0,
                          width: { xs: 32, md: 48 },
                          display: "flex",
                          justifyContent: "center",
                          pt: 2.5,
                        }}
                      >
                        <Box
                          sx={{
                            width: { xs: 12, md: 14 },
                            height: { xs: 12, md: 14 },
                            borderRadius: "50%",
                            bgcolor: release.isUnreleased ? c.warning : isLatest ? c.primary : alpha(c.textSecondary, 0.4),
                            boxShadow: release.isUnreleased
                              ? `0 0 16px ${alpha(c.warning, 0.6)}`
                              : isLatest
                                ? `0 0 20px ${alpha(c.primary, 0.7)}`
                                : "none",
                            border: `2px solid ${alpha(c.bgDefault, 0.9)}`,
                          }}
                        />
                      </Box>

                      {/* Card */}
                      <Box
                        sx={{
                          flex: 1,
                          minWidth: 0,
                          borderRadius: 2.5,
                          border: `1px solid ${release.isUnreleased ? alpha(c.warning, 0.25) : isLatest ? alpha(c.primary, 0.35) : alpha(c.divider, 0.4)}`,
                          bgcolor: "rgba(10,10,22,0.72)",
                          backdropFilter: "blur(20px)",
                          boxShadow: isLatest
                            ? `0 8px 40px rgba(0,0,0,0.45), 0 0 0 1px ${alpha(c.primary, 0.12)}`
                            : "0 4px 24px rgba(0,0,0,0.35)",
                          overflow: "hidden",
                          position: "relative",
                        }}
                      >
                        <Box
                          aria-hidden
                          sx={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            right: 0,
                            height: "40%",
                            background: "linear-gradient(180deg, rgba(255,255,255,0.04) 0%, transparent 100%)",
                            pointerEvents: "none",
                          }}
                        />

                        <Box sx={{ p: { xs: 2.5, md: 3.5 }, position: "relative" }}>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "flex-start",
                              justifyContent: "space-between",
                              flexWrap: "wrap",
                              gap: 1.5,
                              mb: 3,
                            }}
                          >
                            <Box>
                              <Typography
                                component="h2"
                                sx={{
                                  fontSize: { xs: "1.35rem", md: "1.6rem" },
                                  fontWeight: 800,
                                  letterSpacing: "-0.02em",
                                  color: c.textPrimary,
                                  fontFamily: "monospace",
                                  mb: 0.5,
                                }}
                              >
                                {release.isUnreleased ? "Unreleased" : `v${release.version}`}
                              </Typography>
                              {release.date && (
                                <Typography sx={{ color: alpha(c.textSecondary, 0.8), fontSize: "0.85rem" }}>
                                  {formatDate(release.date)}
                                </Typography>
                              )}
                            </Box>
                            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                              {release.isUnreleased ? (
                                <Chip
                                  label="In development"
                                  size="small"
                                  sx={{
                                    bgcolor: alpha(c.warning, 0.12),
                                    color: c.warning,
                                    border: `1px solid ${alpha(c.warning, 0.3)}`,
                                    fontWeight: 600,
                                  }}
                                />
                              ) : isLatest ? (
                                <Chip
                                  icon={<RocketLaunchIcon sx={{ fontSize: "0.85rem !important" }} />}
                                  label="Latest stable"
                                  size="small"
                                  sx={{
                                    bgcolor: alpha(c.primary, 0.12),
                                    color: c.primary,
                                    border: `1px solid ${alpha(c.primary, 0.35)}`,
                                    fontWeight: 600,
                                    "& .MuiChip-icon": { color: c.primary },
                                  }}
                                />
                              ) : (
                                <Chip
                                  label="Released"
                                  size="small"
                                  sx={{
                                    bgcolor: alpha(c.success, 0.1),
                                    color: c.success,
                                    border: `1px solid ${alpha(c.success, 0.25)}`,
                                    fontWeight: 600,
                                  }}
                                />
                              )}
                              <Chip
                                label={`${items} change${items === 1 ? "" : "s"}`}
                                size="small"
                                variant="outlined"
                                sx={{
                                  borderColor: alpha(c.divider, 0.5),
                                  color: c.textSecondary,
                                  fontWeight: 500,
                                }}
                              />
                            </Box>
                          </Box>

                          <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
                            {release.sections.map((section) => {
                              const meta = CATEGORY_META[section.category] ?? {
                                icon: EditOutlinedIcon,
                                color: c.textSecondary,
                              };
                              const Icon = meta.icon;
                              return (
                                <Box key={section.category}>
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.25 }}>
                                    <Box
                                      sx={{
                                        width: 28,
                                        height: 28,
                                        borderRadius: 1,
                                        bgcolor: alpha(meta.color, 0.1),
                                        border: `1px solid ${alpha(meta.color, 0.22)}`,
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                      }}
                                    >
                                      <Icon sx={{ fontSize: 15, color: meta.color }} />
                                    </Box>
                                    <Typography
                                      sx={{
                                        fontSize: "0.72rem",
                                        fontWeight: 700,
                                        textTransform: "uppercase",
                                        letterSpacing: "0.1em",
                                        color: meta.color,
                                      }}
                                    >
                                      {section.category}
                                    </Typography>
                                  </Box>
                                  <Box
                                    component="ul"
                                    sx={{
                                      m: 0,
                                      pl: 0,
                                      listStyle: "none",
                                      display: "flex",
                                      flexDirection: "column",
                                      gap: 0.75,
                                    }}
                                  >
                                    {section.items.map((item) => (
                                      <Box
                                        component="li"
                                        key={item}
                                        sx={{
                                          display: "flex",
                                          gap: 1.25,
                                          color: c.textSecondary,
                                          fontSize: "0.9rem",
                                          lineHeight: 1.65,
                                          pl: 0.5,
                                        }}
                                      >
                                        <Box
                                          component="span"
                                          sx={{
                                            flexShrink: 0,
                                            mt: 0.85,
                                            width: 5,
                                            height: 5,
                                            borderRadius: "50%",
                                            bgcolor: alpha(meta.color, 0.55),
                                          }}
                                        />
                                        <Box component="span">{item}</Box>
                                      </Box>
                                    ))}
                                  </Box>
                                </Box>
                              );
                            })}
                          </Box>
                        </Box>
                      </Box>
                    </Box>
                  </ScrollReveal>
                );
              })}
            </Box>
          </Box>

          {/* Footer CTA */}
          <ScrollReveal delay={0.15}>
            <Box
              sx={{
                mt: 8,
                p: { xs: 3, md: 4 },
                borderRadius: 3,
                border: `1px solid ${alpha(c.divider, 0.4)}`,
                bgcolor: alpha(c.bgPaper, 0.35),
                backdropFilter: "blur(16px)",
                textAlign: "center",
              }}
            >
              <Typography sx={{ fontWeight: 700, color: c.textPrimary, mb: 1, fontSize: "1.1rem" }}>
                Want every commit, not just releases?
              </Typography>
              <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", mb: 3, maxWidth: 420, mx: "auto" }}>
                Follow development on GitHub or watch releases for upgrade notifications.
              </Typography>
              <Box sx={{ display: "flex", gap: 1.5, justifyContent: "center", flexWrap: "wrap" }}>
                <Button
                  component="a"
                  href="https://github.com/malike2356/keprix/commits/main"
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="contained"
                  startIcon={<GitHubIcon />}
                  endIcon={<OpenInNewIcon sx={{ fontSize: "0.85rem !important" }} />}
                  sx={{
                    fontWeight: 700,
                    borderRadius: "9999px",
                    px: 3,
                    background: `linear-gradient(135deg, ${c.primary} 0%, ${c.secondary} 100%)`,
                  }}
                >
                  View commits
                </Button>
                <Button
                  component="a"
                  href="https://github.com/malike2356/keprix/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="outlined"
                  sx={{
                    fontWeight: 600,
                    borderRadius: "9999px",
                    px: 3,
                    borderColor: alpha(c.divider, 0.5),
                    color: c.textSecondary,
                    "&:hover": { borderColor: alpha(c.primary, 0.4), color: c.textPrimary },
                  }}
                >
                  GitHub releases
                </Button>
              </Box>
            </Box>
          </ScrollReveal>
        </Container>
      </Box>
    </Box>
  );
}

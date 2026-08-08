"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import PolicyIcon from "@mui/icons-material/Policy";
import ShieldIcon from "@mui/icons-material/Shield";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

const STEPS = [
  {
    icon: AutoFixHighIcon,
    title: "Keprix proposes",
    body: "When a task needs a missing capability, Keprix proposes a tool, workflow, or code change instead of stopping.",
  },
  {
    icon: FactCheckIcon,
    title: "Tests first",
    body: "Each proposal is checked and summarized with the evidence an operator needs before any runtime change can begin.",
  },
  {
    icon: ShieldIcon,
    title: "You approve",
    body: "Mutation stays behind approval gates, so Keprix waits for a human decision before install, deploy, or upgrade steps.",
  },
  {
    icon: PolicyIcon,
    title: "Scout governs",
    body: "Pair Keprix with Scout for governance, audit trails, policy enforcement, and kill-switch control across higher-risk production work today.",
  },
] as const;

export function MutationGovernanceBand() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 10, md: 14 },
        bgcolor: c.bgDefault,
        borderTop: `1px solid ${alpha(c.divider, 0.8)}`,
        borderBottom: `1px solid ${alpha(c.divider, 0.8)}`,
      }}
    >
      <Container maxWidth="lg">
        <ScrollReveal>
          <Box sx={{ maxWidth: 760, mx: "auto", textAlign: "center", mb: { xs: 5, md: 7 } }}>
            <Typography
              component="p"
              sx={{
                ...MARKETING_EYEBROW_SX,
                color: c.primary,
                mb: 2,
              }}
            >
              Controlled mutation
            </Typography>
            <Typography
              component="h2"
              sx={{
                ...MARKETING_HEADING_SX,
                color: c.textPrimary,
                fontSize: { xs: "2.2rem", md: "3rem" },
                mb: 2,
              }}
            >
              Keprix mutates. Scout governs.
            </Typography>
            <Typography
              sx={{
                color: c.textSecondary,
                fontSize: { xs: "0.98rem", md: "1.05rem" },
                lineHeight: 1.75,
                maxWidth: 640,
                mx: "auto",
              }}
            >
              Self-mutating does not mean uncontrolled. Keprix proposes and tests the
              upgrade. You approve the change. Scout can add governance, audit trails,
              and kill-switch control where the risk demands it.
            </Typography>
          </Box>
        </ScrollReveal>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, minmax(0, 1fr))" },
            gap: 2,
          }}
        >
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <ScrollReveal key={step.title} delay={index * 0.05}>
                <Box
                  sx={{
                    height: "100%",
                    p: 2.5,
                    borderRadius: 2,
                    bgcolor: alpha(c.bgCard, 0.7),
                    border: `1px solid ${alpha(c.divider, 0.9)}`,
                  }}
                >
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: 1.5,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      bgcolor: alpha(c.primary, 0.1),
                      border: `1px solid ${alpha(c.primary, 0.24)}`,
                      mb: 2,
                    }}
                  >
                    <Icon sx={{ color: c.primary, fontSize: 20 }} />
                  </Box>
                  <Typography sx={{ color: c.textPrimary, fontWeight: 750, mb: 1, fontSize: "0.98rem" }}>
                    {step.title}
                  </Typography>
                  <Typography sx={{ color: c.textSecondary, fontSize: "0.86rem", lineHeight: 1.65 }}>
                    {step.body}
                  </Typography>
                </Box>
              </ScrollReveal>
            );
          })}
        </Box>

        <ScrollReveal delay={0.18}>
          <Box sx={{ display: "flex", justifyContent: "center", mt: { xs: 4, md: 5 } }}>
            <Button
              component="a"
              href="https://labyrinthscout.com"
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              endIcon={<OpenInNewIcon />}
              sx={{
                borderRadius: "9999px",
                px: 3,
                fontWeight: 700,
                borderColor: alpha(c.primary, 0.38),
                color: c.textPrimary,
                bgcolor: alpha(c.primary, 0.04),
                "&:hover": {
                  borderColor: c.primary,
                  bgcolor: alpha(c.primary, 0.09),
                },
              }}
            >
              Visit Scout
            </Button>
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}

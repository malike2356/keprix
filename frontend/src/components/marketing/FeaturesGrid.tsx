"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import HubIcon from "@mui/icons-material/Hub";
import MemoryIcon from "@mui/icons-material/Memory";
import ShieldIcon from "@mui/icons-material/Shield";
import CodeIcon from "@mui/icons-material/Code";
import StorefrontIcon from "@mui/icons-material/Storefront";
import ExtensionIcon from "@mui/icons-material/Extension";
import LockIcon from "@mui/icons-material/Lock";
import {
  MARKETING_BTN_RADIUS,
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { MARKETING_FEATURE_HIGHLIGHTS } from "@/lib/marketing-features-catalog";

const HIGHLIGHT_ICONS = {
  tui: CodeIcon,
  "agent-os": HubIcon,
  "channel-shield": ShieldIcon,
  crm: StorefrontIcon,
  memory: MemoryIcon,
  mutation: AutoFixHighIcon,
  sidecar: ExtensionIcon,
  vault: LockIcon,
} as const;

export function FeaturesGrid() {
  const c = useMarketingColors();

  const features = MARKETING_FEATURE_HIGHLIGHTS.map((item) => ({
    ...item,
    icon: HIGHLIGHT_ICONS[item.id],
  }));

  return (
    <Box
      id="features"
      sx={{
        py: { xs: 10, md: 14 },
        position: "relative",
        bgcolor: c.bgDefault,
      }}
    >
      <Container maxWidth="lg">
        <ScrollReveal>
          <Box sx={{ mb: 8, maxWidth: 640 }}>
            <Typography
              component="p"
              sx={{
                ...MARKETING_EYEBROW_SX,
                color: c.primary,
                mb: 1.5,
              }}
            >
              Capabilities
            </Typography>
            <Typography
              component="h2"
              sx={{
                ...MARKETING_HEADING_SX,
                fontSize: { xs: "2rem", md: "2.75rem" },
                mb: 2,
                color: c.textPrimary,
              }}
            >
              One runtime for agents, approvals, and ops.
            </Typography>
            <Typography sx={{ color: c.textSecondary, fontSize: "1rem", lineHeight: 1.7 }}>
              Self-hosted agent OS with CRM, sidecars, Soft Wall approvals, and reviewable
              self-coding. MIT licensed. No vendor lock-in.
            </Typography>
          </Box>
        </ScrollReveal>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr 1fr" },
            gap: 0,
            borderTop: `1px solid ${c.divider}`,
            borderLeft: `1px solid ${c.divider}`,
          }}
        >
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <ScrollReveal key={f.title} delay={i * 0.04}>
                <Box
                  sx={{
                    height: "100%",
                    p: 3,
                    borderRight: `1px solid ${c.divider}`,
                    borderBottom: `1px solid ${c.divider}`,
                    bgcolor: c.bgDefault,
                    transition: "background-color 0.15s ease",
                    "&:hover": {
                      bgcolor: alpha(c.primary, 0.04),
                    },
                  }}
                >
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      mb: 2,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: `1px solid ${c.divider}`,
                      borderRadius: "4px",
                      color: c.textPrimary,
                    }}
                  >
                    <Icon sx={{ fontSize: 18 }} />
                  </Box>
                  <Typography
                    sx={{
                      fontWeight: 600,
                      color: c.textPrimary,
                      mb: 1,
                      fontSize: "0.98rem",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {f.title}
                  </Typography>
                  <Typography sx={{ fontSize: "0.875rem", color: c.textSecondary, lineHeight: 1.65 }}>
                    {f.body}
                  </Typography>
                </Box>
              </ScrollReveal>
            );
          })}
        </Box>

        <ScrollReveal delay={0.15}>
          <Box sx={{ mt: 5 }}>
            <Button
              component="a"
              href="/features"
              variant="outlined"
              size="large"
              sx={{
                textTransform: "none",
                fontWeight: 600,
                px: 2.5,
                borderRadius: MARKETING_BTN_RADIUS,
                borderColor: c.divider,
                color: c.textPrimary,
                "&:hover": {
                  borderColor: c.primary,
                  bgcolor: alpha(c.primary, 0.04),
                },
              }}
            >
              See full capabilities list
            </Button>
            <Typography sx={{ mt: 1.25, fontSize: "0.85rem", color: c.textSecondary }}>
              Every module by name, description, and what it is used for.
            </Typography>
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}

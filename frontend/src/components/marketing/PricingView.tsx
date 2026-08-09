"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import { alpha } from "@mui/material/styles";
import useSWR from "swr";
import SaasPricingPlans from "@/components/marketing/SaasPricingPlans";
import {
  MARKETING_HEADING_SX,
  getMarketingColors,
} from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";
import { fetchBillingStatus } from "@/lib/billing-api";

const FREE_FEATURES = [
  "Full agent runtime - every Community feature",
  "Web workspace, Command Center TUI, CLI, and API",
  "Agentic CRM, Soft Wall, and Companies House research",
  "Channel Shield inbound protection",
  "Universal Sidecar contract for product packs",
  "Unlimited conversations and tool synthesis (Mutation engine)",
  "LLM provider routing including Ollama",
  "Telegram, Discord, web UI, and REST API",
  "Memory, Brain graph, and RAG pipelines",
  "Playbooks, Agent Apps, skills, and cron",
  "Vault, ACLs, and optional governance connectors",
  "Self-hosted on your own hardware",
  "MIT license - commercial use allowed",
] as const;

function OssPricingSection({ c }: { c: ReturnType<typeof getMarketingColors> }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
      <Card
        sx={{
          bgcolor: alpha(c.bgPaper, 0.6),
          border: `2px solid ${alpha(c.primary, 0.4)}`,
          borderRadius: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Chip
            label="Free forever"
            size="small"
            sx={{
              mb: 2,
              bgcolor: alpha(c.success, 0.12),
              color: c.success,
              border: `1px solid ${alpha(c.success, 0.3)}`,
              fontWeight: 700,
            }}
          />
          <Typography sx={{ fontWeight: 800, fontSize: "1.5rem", color: c.textPrimary, mb: 0.5 }}>
            Self-hosted
          </Typography>
          <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", mb: 3 }}>
            MIT license. Run it anywhere.
          </Typography>
          <Typography sx={{ fontSize: "3rem", fontWeight: 800, color: c.textPrimary, lineHeight: 1 }}>
            $0
          </Typography>
          <Typography sx={{ color: c.textSecondary, fontSize: "0.85rem", mb: 3 }}>
            forever
          </Typography>
          <Button component="a" href="/auth/setup" variant="contained" fullWidth size="large" sx={{ fontWeight: 700 }}>
            Deploy now
          </Button>
          <List dense sx={{ mt: 3 }}>
            {FREE_FEATURES.map((feature) => (
              <ListItem key={feature} disablePadding sx={{ mb: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <CheckIcon sx={{ color: c.success, fontSize: 18 }} />
                </ListItemIcon>
                <ListItemText
                  primary={feature}
                  primaryTypographyProps={{ sx: { fontSize: "0.85rem", color: c.textSecondary } }}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      <Card
        sx={{
          bgcolor: alpha(c.bgPaper, 0.3),
          border: `1px solid ${alpha(c.divider, 0.4)}`,
          borderRadius: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Chip
            label="Optional add-on"
            size="small"
            sx={{
              mb: 2,
              bgcolor: alpha(c.bgPaper, 0.8),
              color: alpha(c.textSecondary, 0.7),
              border: `1px solid ${alpha(c.divider, 0.5)}`,
              fontWeight: 600,
            }}
          />
          <Typography sx={{ fontWeight: 800, fontSize: "1.5rem", color: c.textPrimary, mb: 0.5 }}>
            Governance Connector
          </Typography>
          <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", mb: 3 }}>
            Optional add-on from a governance provider or Keprix extension.
          </Typography>
          <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", lineHeight: 1.7, mb: 3 }}>
            Teams that need kill switches, tamper-evident audit trails, and operator-defined policies can connect
            a governance provider. Keprix works without one.
          </Typography>
          <Button
            component="a"
            href="/settings/governance"
            variant="outlined"
            fullWidth
            size="large"
            sx={{ fontWeight: 600 }}
          >
            Configure governance
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}

export function PricingView() {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const { data: billing } = useSWR("pricing-billing-status", fetchBillingStatus);
  const billingEnabled = billing?.enabled === true && (billing.plans?.length ?? 0) > 0;

  return (
    <Box sx={{ pt: { xs: 14, md: 18 }, pb: { xs: 10, md: 14 }, bgcolor: c.bgDefault, minHeight: "100%", transition: "background-color 0.25s ease" }}>
      <Container maxWidth={billingEnabled ? "lg" : "md"}>
        <Box sx={{ textAlign: "center", mb: billingEnabled ? 6 : 8 }}>
          <Typography
            component="h1"
            sx={{
              ...MARKETING_HEADING_SX,
              fontSize: { xs: "2.2rem", md: "3.15rem" },
              color: c.textPrimary,
              mb: 2,
            }}
          >
            {billingEnabled ? `${billing?.product_name || "Subscription"} plans` : "Simple pricing."}
          </Typography>
          <Typography sx={{ color: c.textSecondary, fontSize: "1.1rem" }}>
            {billingEnabled
              ? billing?.trial_days && billing.trial_days > 0
                ? `Paid plans include a ${billing.trial_days}-day trial. Manage billing in the app after sign-in.`
                : "Choose a plan, then sign in to manage billing in the workspace."
              : "One tier. Free. No exceptions."}
          </Typography>
        </Box>

        {billingEnabled ? (
          <>
            <Box sx={{ mb: 4, p: 3, borderRadius: 2, bgcolor: alpha(c.bgPaper, 0.5), border: `1px solid ${alpha(c.divider, 0.4)}` }}>
              <Typography sx={{ fontWeight: 700, color: c.textPrimary, mb: 1 }}>
                Agent Apps
              </Typography>
              <Typography sx={{ color: c.textSecondary, fontSize: "0.95rem", lineHeight: 1.7 }}>
                Community: up to 3 installed apps, 50 runs/month, free marketplace templates. Pro: 10 apps,
                500 runs/month, pro templates, scheduled runs. Team: webhooks and bundle publishing. See plan
                feature flags below for your instance.
              </Typography>
            </Box>
            <SaasPricingPlans plans={billing.plans || []} trialDays={billing.trial_days} />
            <Divider sx={{ my: 6, borderColor: alpha(c.divider, 0.4) }} />
            <Box sx={{ textAlign: "center", mb: 4 }}>
              <Typography sx={{ fontWeight: 700, fontSize: "1.25rem", color: c.textPrimary, mb: 1 }}>
                Prefer to self-host?
              </Typography>
              <Typography sx={{ color: c.textSecondary, fontSize: "0.95rem" }}>
                Keprix core remains open source. Deploy on your own hardware at no cost.
              </Typography>
            </Box>
            <OssPricingSection c={c} />
          </>
        ) : (
          <OssPricingSection c={c} />
        )}
      </Container>
    </Box>
  );
}

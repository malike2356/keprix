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
import Link from "next/link";
import useSWR from "swr";
import SaasPricingPlans from "@/components/marketing/SaasPricingPlans";
import { fetchBillingStatus } from "@/lib/billing-api";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";

const FREE_FEATURES = [
  "Full agent runtime - every feature",
  "Unlimited conversations",
  "Unlimited tool synthesis (Mutation engine)",
  "All 23 LLM provider integrations",
  "Telegram, Discord, web UI, and REST API",
  "Conversation memory and vector search",
  "Multi-agent teams and playbooks",
  "Browser automation",
  "Self-hosted on your own hardware",
  "MIT license - commercial use allowed",
] as const;

function OssPricingSection() {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
      <Card
        sx={{
          bgcolor: alpha(KEPRIX_COLORS.bgPaper, 0.6),
          border: `2px solid ${alpha(KEPRIX_COLORS.primary, 0.4)}`,
          borderRadius: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Chip
            label="Free forever"
            size="small"
            sx={{
              mb: 2,
              bgcolor: alpha(KEPRIX_COLORS.success, 0.12),
              color: KEPRIX_COLORS.success,
              border: `1px solid ${alpha(KEPRIX_COLORS.success, 0.3)}`,
              fontWeight: 700,
            }}
          />
          <Typography sx={{ fontWeight: 800, fontSize: "1.5rem", color: KEPRIX_COLORS.textPrimary, mb: 0.5 }}>
            Self-hosted
          </Typography>
          <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.9rem", mb: 3 }}>
            MIT license. Run it anywhere.
          </Typography>
          <Typography sx={{ fontSize: "3rem", fontWeight: 800, color: KEPRIX_COLORS.textPrimary, lineHeight: 1 }}>
            $0
          </Typography>
          <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.85rem", mb: 3 }}>
            forever
          </Typography>
          <Button component={Link} href="/auth/setup" variant="contained" fullWidth size="large" sx={{ fontWeight: 700 }}>
            Deploy now
          </Button>
          <List dense sx={{ mt: 3 }}>
            {FREE_FEATURES.map((feature) => (
              <ListItem key={feature} disablePadding sx={{ mb: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 28 }}>
                  <CheckIcon sx={{ color: KEPRIX_COLORS.success, fontSize: 18 }} />
                </ListItemIcon>
                <ListItemText
                  primary={feature}
                  primaryTypographyProps={{ sx: { fontSize: "0.85rem", color: KEPRIX_COLORS.textSecondary } }}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      <Card
        sx={{
          bgcolor: alpha(KEPRIX_COLORS.bgPaper, 0.3),
          border: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.4)}`,
          borderRadius: 3,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Chip
            label="Optional add-on"
            size="small"
            sx={{
              mb: 2,
              bgcolor: alpha(KEPRIX_COLORS.bgPaper, 0.8),
              color: alpha(KEPRIX_COLORS.textSecondary, 0.7),
              border: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.5)}`,
              fontWeight: 600,
            }}
          />
          <Typography sx={{ fontWeight: 800, fontSize: "1.5rem", color: KEPRIX_COLORS.textPrimary, mb: 0.5 }}>
            Governance Connector
          </Typography>
          <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.9rem", mb: 3 }}>
            Optional add-on from a governance provider or Keprix extension.
          </Typography>
          <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.9rem", lineHeight: 1.7, mb: 3 }}>
            Teams that need kill switches, tamper-evident audit trails, and operator-defined policies can connect
            a governance provider. Keprix works without one.
          </Typography>
          <Button
            component={Link}
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
  const { data: billing } = useSWR("pricing-billing-status", fetchBillingStatus);
  const billingEnabled = billing?.enabled === true && (billing.plans?.length ?? 0) > 0;

  return (
    <Box sx={{ pt: { xs: 14, md: 18 }, pb: { xs: 10, md: 14 } }}>
      <Container maxWidth={billingEnabled ? "lg" : "md"}>
        <Box sx={{ textAlign: "center", mb: billingEnabled ? 6 : 8 }}>
          <Typography
            component="h1"
            sx={{
              fontSize: { xs: "2rem", md: "3rem" },
              fontWeight: 800,
              letterSpacing: "-0.02em",
              color: KEPRIX_COLORS.textPrimary,
              mb: 2,
            }}
          >
            {billingEnabled ? `${billing?.product_name || "Subscription"} plans` : "Simple pricing."}
          </Typography>
          <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "1.1rem" }}>
            {billingEnabled
              ? billing?.trial_days && billing.trial_days > 0
                ? `Paid plans include a ${billing.trial_days}-day trial. Manage billing in the app after sign-in.`
                : "Choose a plan, then sign in to manage billing in the workspace."
              : "One tier. Free. No exceptions."}
          </Typography>
        </Box>

        {billingEnabled ? (
          <>
            <Box sx={{ mb: 4, p: 3, borderRadius: 2, bgcolor: alpha(KEPRIX_COLORS.bgPaper, 0.5), border: `1px solid ${alpha(KEPRIX_COLORS.divider, 0.4)}` }}>
              <Typography sx={{ fontWeight: 700, color: KEPRIX_COLORS.textPrimary, mb: 1 }}>
                Agent Apps
              </Typography>
              <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.95rem", lineHeight: 1.7 }}>
                Community: up to 3 installed apps, 50 runs/month, free marketplace templates. Pro: 10 apps,
                500 runs/month, pro templates, scheduled runs. Team: webhooks and bundle publishing. See plan
                feature flags below for your instance.
              </Typography>
            </Box>
            <SaasPricingPlans plans={billing.plans || []} trialDays={billing.trial_days} />
            <Divider sx={{ my: 6, borderColor: alpha(KEPRIX_COLORS.divider, 0.4) }} />
            <Box sx={{ textAlign: "center", mb: 4 }}>
              <Typography sx={{ fontWeight: 700, fontSize: "1.25rem", color: KEPRIX_COLORS.textPrimary, mb: 1 }}>
                Prefer to self-host?
              </Typography>
              <Typography sx={{ color: KEPRIX_COLORS.textSecondary, fontSize: "0.95rem" }}>
                Keprix core remains open source. Deploy on your own hardware at no cost.
              </Typography>
            </Box>
            <OssPricingSection />
          </>
        ) : (
          <OssPricingSection />
        )}
      </Container>
    </Box>
  );
}

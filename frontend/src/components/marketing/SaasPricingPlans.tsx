"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import { alpha } from "@mui/material/styles";
import Link from "next/link";
import * as React from "react";
import type { BillingInterval } from "@/components/billing/billing-types";
import type { BillingPlan } from "@/lib/billing-api";
import { formatFeatureValue, formatMoneyMinorUnits } from "@/lib/billing-format";
import { getMarketingColors } from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

type SaasPricingPlansProps = {
  plans: BillingPlan[];
  trialDays?: number;
};

function selectPrice(plan: BillingPlan, interval: BillingInterval) {
  const prices = plan.prices || [];
  if (prices.length === 0) return null;
  return prices.find((price) => price.interval === interval) || prices[0];
}

function isFreePlan(plan: BillingPlan): boolean {
  const price = selectPrice(plan, "month");
  return !price || price.amount === 0;
}

export default function SaasPricingPlans({ plans, trialDays }: SaasPricingPlansProps) {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const [interval, setInterval] = React.useState<BillingInterval>("month");
  const hasPaidPrices = plans.some((plan) => plan.prices?.some((price) => price.amount > 0));

  return (
    <Box>
      {hasPaidPrices ? (
        <Box sx={{ display: "flex", justifyContent: "center", mb: 4 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={interval}
            onChange={(_event, value: BillingInterval | null) => {
              if (value) setInterval(value);
            }}
          >
            <ToggleButton value="month">Monthly</ToggleButton>
            <ToggleButton value="year">Yearly</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: `repeat(${Math.min(plans.length, 3)}, 1fr)` },
          gap: 3,
          mb: 6,
        }}
      >
        {plans.map((plan) => {
          const price = selectPrice(plan, interval);
          const free = isFreePlan(plan);
          const highlight = Boolean(plan.metadata?.highlight);
          const badge = typeof plan.metadata?.badge === "string" ? plan.metadata.badge : null;
          const features = Object.entries(plan.feature_flags || {}).slice(0, 6);
          const ctaHref = free ? "/auth/setup" : "/auth/login?next=/settings/billing";
          const ctaLabel = free ? "Get started" : trialDays && trialDays > 0 ? `Start ${trialDays}-day trial` : "Subscribe";

          return (
            <Card
              key={plan.id}
              sx={{
                bgcolor: alpha(c.bgPaper, highlight ? 0.75 : 0.45),
                border: highlight
                  ? `2px solid ${alpha(c.primary, 0.5)}`
                  : `1px solid ${alpha(c.divider, 0.45)}`,
                borderRadius: 3,
                height: "100%",
              }}
            >
              <CardContent sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column" }}>
                {badge ? (
                  <Chip
                    label={badge}
                    size="small"
                    sx={{
                      mb: 1.5,
                      alignSelf: "flex-start",
                      bgcolor: alpha(c.primary, 0.15),
                      color: c.primary,
                      fontWeight: 700,
                    }}
                  />
                ) : null}
                <Typography sx={{ fontWeight: 800, fontSize: "1.35rem", color: c.textPrimary, mb: 0.5 }}>
                  {plan.name}
                </Typography>
                <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", mb: 2, minHeight: 40 }}>
                  {plan.description}
                </Typography>
                <Typography sx={{ fontSize: "2.5rem", fontWeight: 800, color: c.textPrimary, lineHeight: 1 }}>
                  {free ? "$0" : formatMoneyMinorUnits(price?.amount || 0, price?.currency || "gbp")}
                </Typography>
                <Typography sx={{ color: c.textSecondary, fontSize: "0.85rem", mb: 2 }}>
                  {free ? "forever" : price?.interval ? `per ${price.interval}` : ""}
                </Typography>
                <Button
                  component={Link}
                  href={ctaHref}
                  variant={highlight ? "contained" : "outlined"}
                  fullWidth
                  size="large"
                  sx={{ fontWeight: 700, mb: 2 }}
                >
                  {ctaLabel}
                </Button>
                <List dense sx={{ mt: "auto" }}>
                  {features.map(([key, value]) => (
                    <ListItem key={key} disablePadding sx={{ mb: 0.35 }}>
                      <ListItemIcon sx={{ minWidth: 26 }}>
                        <CheckIcon sx={{ color: c.success, fontSize: 16 }} />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${key.replace(/_/g, " ")}: ${formatFeatureValue(value)}`}
                        primaryTypographyProps={{
                          sx: { fontSize: "0.8rem", color: c.textSecondary, textTransform: "capitalize" },
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
}

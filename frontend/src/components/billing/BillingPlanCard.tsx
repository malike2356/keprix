"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import type { BillingInterval } from "@/components/billing/billing-types";
import type { BillingPlan } from "@/lib/billing-api";
import { formatFeatureValue, formatMoneyMinorUnits } from "@/lib/billing-format";

type BillingPlanCardProps = {
  plan: BillingPlan;
  interval: BillingInterval;
  currentPlanId?: string | null;
  hasSubscription: boolean;
  trialDays?: number;
  loading?: boolean;
  onStartTrial: (planId: string) => void;
  onSubscribe: (planId: string, interval: BillingInterval) => void;
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

export default function BillingPlanCard({
  plan,
  interval,
  currentPlanId,
  hasSubscription,
  trialDays,
  loading,
  onStartTrial,
  onSubscribe,
}: BillingPlanCardProps) {
  const price = selectPrice(plan, interval);
  const isCurrent = currentPlanId === plan.id;
  const free = isFreePlan(plan);
  const highlight = Boolean(plan.metadata?.highlight);
  const badge = typeof plan.metadata?.badge === "string" ? plan.metadata.badge : null;
  const featureEntries = Object.entries(plan.feature_flags || {}).slice(0, 5);

  let actionLabel = "Subscribe";
  let actionHandler = () => onSubscribe(plan.id, interval);

  if (isCurrent) {
    actionLabel = "Current plan";
  } else if (free) {
    actionLabel = hasSubscription ? "Included" : "Start";
    actionHandler = () => onSubscribe(plan.id, interval);
  } else if (!hasSubscription && trialDays && trialDays > 0) {
    actionLabel = "Start trial";
    actionHandler = () => onStartTrial(plan.id);
  } else if (hasSubscription) {
    actionLabel = "Upgrade";
  }

  return (
    <DashboardCard
      title={plan.name}
      subtitle={plan.description}
      action={
        badge ? <Chip size="small" color="primary" label={badge} /> : null
      }
    >
      <Box
        sx={{
          border: highlight ? 2 : 1,
          borderColor: highlight ? "primary.main" : "divider",
          borderRadius: 2,
          p: 2,
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Typography variant="h4" sx={{ mb: 0.5 }}>
          {free ? "Free" : formatMoneyMinorUnits(price?.amount || 0, price?.currency || "gbp")}
        </Typography>
        {!free && price?.interval ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            per {price.interval}
            {price.discount_text ? ` (${price.discount_text})` : ""}
          </Typography>
        ) : null}

        <List dense sx={{ flex: 1, mb: 2 }}>
          {featureEntries.map(([key, value]) => (
            <ListItem key={key} disableGutters sx={{ py: 0.25 }}>
              <ListItemText
                primary={key.replace(/_/g, " ")}
                secondary={formatFeatureValue(value)}
                primaryTypographyProps={{ variant: "body2", textTransform: "capitalize" }}
                secondaryTypographyProps={{ variant: "caption" }}
              />
            </ListItem>
          ))}
        </List>

        <Button
          variant={highlight ? "contained" : "outlined"}
          fullWidth
          disabled={isCurrent || loading}
          onClick={actionHandler}
        >
          {actionLabel}
        </Button>
      </Box>
    </DashboardCard>
  );
}

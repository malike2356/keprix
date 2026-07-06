"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import type { BillingPlan, BillingSubscription } from "@/lib/billing-api";
import { daysUntil, formatBillingDate } from "@/lib/billing-format";

type BillingSubscriptionSummaryProps = {
  plan?: BillingPlan | null;
  subscription: BillingSubscription | null;
  productName?: string;
  trialDays?: number;
  loading?: boolean;
  onCancel: () => void;
  onResume: () => void;
  actionLoading?: boolean;
};

function statusColor(status: string | undefined): "default" | "success" | "warning" | "error" {
  switch (status) {
    case "active":
      return "success";
    case "trialing":
      return "warning";
    case "past_due":
      return "error";
    case "cancelled":
    case "canceled":
      return "default";
    default:
      return "default";
  }
}

export default function BillingSubscriptionSummary({
  plan,
  subscription,
  productName,
  trialDays,
  loading,
  onCancel,
  onResume,
  actionLoading,
}: BillingSubscriptionSummaryProps) {
  const planName = plan?.name || subscription?.plan_id || "No plan";
  const status = subscription?.status || "none";
  const trialDaysLeft = daysUntil(subscription?.trial_ends_at);

  return (
    <DashboardCard title="Current subscription" subtitle={productName}>
      {loading ? (
        <SkeletonDetailPanel fields={4} />
      ) : (
        <Stack spacing={2}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography variant="h5">{planName}</Typography>
            <Chip size="small" label={status} color={statusColor(status)} />
          </Box>

          {status === "trialing" && trialDaysLeft !== null ? (
            <Typography variant="body2" color="text.secondary">
              Trial ends {formatBillingDate(subscription?.trial_ends_at)} ({trialDaysLeft} day
              {trialDaysLeft === 1 ? "" : "s"} left)
            </Typography>
          ) : null}

          {subscription?.current_period_end ? (
            <Typography variant="body2" color="text.secondary">
              Renews on {formatBillingDate(subscription.current_period_end)}
            </Typography>
          ) : null}

          {!subscription && trialDays && trialDays > 0 ? (
            <Typography variant="body2" color="text.secondary">
              Paid plans include a {trialDays}-day trial.
            </Typography>
          ) : null}

          {subscription?.cancel_at_period_end ? (
            <AlertRow onResume={onResume} actionLoading={actionLoading} />
          ) : subscription && status !== "none" && status !== "cancelled" ? (
            <Box>
              <Button size="small" color="warning" onClick={onCancel} disabled={actionLoading}>
                Cancel at period end
              </Button>
            </Box>
          ) : null}
        </Stack>
      )}
    </DashboardCard>
  );
}

function AlertRow({ onResume, actionLoading }: { onResume: () => void; actionLoading?: boolean }) {
  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 1,
        bgcolor: "warning.light",
        color: "warning.contrastText",
      }}
    >
      <Typography variant="body2" sx={{ mb: 1 }}>
        Your subscription will cancel at the end of the current billing period.
      </Typography>
      <Button size="small" variant="contained" color="inherit" onClick={onResume} disabled={actionLoading}>
        Resume subscription
      </Button>
    </Box>
  );
}

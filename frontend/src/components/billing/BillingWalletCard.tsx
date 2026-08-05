"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock } from "@/components/ui/loading";
import { fetchWalletStatus } from "@/lib/billing-api";

function formatCredits(value: number | undefined): string {
  if (value == null) return "-";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);
}

export default function BillingWalletCard() {
  const { data, error, isLoading } = useSWR("billing-wallet-status", fetchWalletStatus);

  if (isLoading) {
    return (
      <DashboardCard title="AI wallet">
        <SkeletonBlock height={120} />
      </DashboardCard>
    );
  }

  if (error || !data) {
    return (
      <DashboardCard title="AI wallet">
        <Alert severity="error">
          {error instanceof Error ? error.message : "Could not load AI wallet status"}
        </Alert>
      </DashboardCard>
    );
  }

  const balance = data.wallet?.balance_credits ?? 0;
  const included = data.policy?.included_credits_monthly ?? 0;
  const usedPercent = included > 0 ? Math.min(100, Math.max(0, 100 - (balance / included) * 100)) : 0;

  return (
    <DashboardCard
      title="AI wallet"
      subtitle={data.hosted ? "Managed AI credits" : "Bring your own key"}
      action={
        data.low_credit || data.exhausted ? (
          <Chip
            size="small"
            color={data.exhausted ? "error" : "warning"}
            label={data.exhausted ? "Exhausted" : "Low credit"}
          />
        ) : null
      }
    >
      <Stack spacing={1.5}>
        <Box>
          <Typography variant="h4">{formatCredits(balance)}</Typography>
          <Typography variant="body2" color="text.secondary">
            credits remaining
          </Typography>
        </Box>
        {included > 0 ? (
          <Box>
            <LinearProgress
              variant="determinate"
              value={usedPercent}
              color={data.exhausted ? "error" : data.low_credit ? "warning" : "primary"}
              sx={{ borderRadius: 1, height: 6 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
              {formatCredits(included)} included credits per month
            </Typography>
          </Box>
        ) : null}
        {data.daily_cap != null ? (
          <Typography variant="body2" color="text.secondary">
            Daily usage: {formatCredits(data.daily_credits_used)} / {formatCredits(data.daily_cap)}
          </Typography>
        ) : null}
        {data.byok_available ? (
          <Typography variant="caption" color="text.secondary">
            Bring-your-own-key is available for unmetered usage.
          </Typography>
        ) : null}
        {data.exhausted && data.actions_when_exhausted?.length ? (
          <Alert severity="warning" sx={{ mt: 1 }}>
            {data.actions_when_exhausted.join(", ")}
          </Alert>
        ) : null}
      </Stack>
    </DashboardCard>
  );
}

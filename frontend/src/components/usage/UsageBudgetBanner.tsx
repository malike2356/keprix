"use client";

import Alert from "@mui/material/Alert";
import type { UsageBudgetStatus } from "@/lib/usage-api";
import { formatUsdCost } from "@/lib/usage-format";

type UsageBudgetBannerProps = {
  budget?: UsageBudgetStatus | null;
};

export default function UsageBudgetBanner({ budget }: UsageBudgetBannerProps) {
  if (!budget?.monthly_budget_usd || !budget.alert) {
    return null;
  }

  const spent = formatUsdCost(budget.spent_usd, "estimated");
  const limit = formatUsdCost(budget.monthly_budget_usd, "estimated");
  const percent = budget.percent_used ?? 0;

  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      Monthly LLM budget alert: {spent} spent of {limit} ({percent.toFixed(1)}% used).
    </Alert>
  );
}

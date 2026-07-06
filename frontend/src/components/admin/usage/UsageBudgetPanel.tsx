"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import type { UsageBudgetStatus } from "@/lib/usage-api";
import { formatUsdCost } from "@/lib/usage-format";

type UsageBudgetPanelProps = {
  budget?: UsageBudgetStatus | null;
  onSave: (body: { monthly_budget_usd: number | null; alert_threshold_percent: number }) => Promise<void>;
  saving?: boolean;
  message?: string | null;
  error?: string | null;
};

export default function UsageBudgetPanel({
  budget,
  onSave,
  saving = false,
  message,
  error,
}: UsageBudgetPanelProps) {
  const [monthlyBudget, setMonthlyBudget] = React.useState("");
  const [threshold, setThreshold] = React.useState(80);

  React.useEffect(() => {
    if (budget?.monthly_budget_usd != null) {
      setMonthlyBudget(String(budget.monthly_budget_usd));
    } else {
      setMonthlyBudget("");
    }
    setThreshold(budget?.alert_threshold_percent ?? 80);
  }, [budget]);

  const spent = budget?.spent_usd ?? 0;
  const limit = budget?.monthly_budget_usd ?? null;
  const percentUsed = limit && limit > 0 ? Math.min(100, (spent / limit) * 100) : 0;

  const handleSave = async () => {
    const parsed = monthlyBudget.trim() === "" ? null : Number(monthlyBudget);
    if (parsed !== null && (!Number.isFinite(parsed) || parsed < 0)) {
      return;
    }
    await onSave({
      monthly_budget_usd: parsed,
      alert_threshold_percent: threshold,
    });
  };

  return (
    <DashboardCard title="Monthly LLM budget" subtitle="Instance-wide spend cap and alert threshold">
      {message ? <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert> : null}
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
        <TextField
          label="Monthly budget (USD)"
          type="number"
          value={monthlyBudget}
          onChange={(event) => setMonthlyBudget(event.target.value)}
          inputProps={{ min: 0, step: 0.01 }}
          helperText="Leave blank to disable budget alerts"
        />
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Alert threshold: {threshold}%
          </Typography>
          <Slider
            value={threshold}
            min={50}
            max={100}
            step={5}
            marks
            valueLabelDisplay="auto"
            onChange={(_event, value) => setThreshold(value as number)}
            aria-label="Budget alert threshold percent"
          />
        </Box>
      </Box>
      {limit && limit > 0 ? (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
            <Typography variant="body2" color="text.secondary">
              Month to date: {formatUsdCost(spent, "estimated")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {percentUsed.toFixed(1)}% of {formatUsdCost(limit, "estimated")}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={percentUsed}
            color={percentUsed >= threshold ? "warning" : "primary"}
          />
        </Box>
      ) : null}
      <Box sx={{ mt: 2 }}>
        <Button variant="contained" disabled={saving} onClick={() => void handleSave()}>
          Save budget
        </Button>
      </Box>
    </DashboardCard>
  );
}

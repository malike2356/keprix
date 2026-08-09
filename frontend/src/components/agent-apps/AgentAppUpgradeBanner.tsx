"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { fetchAgentAppUsage, type AgentAppUsage } from "@/lib/agent-apps-api";

function usagePercent(usage: AgentAppUsage, key: "runs" | "installed") {
  if (key === "runs") {
    if (usage.runs_limit == null || usage.runs_limit <= 0) return 0;
    return Math.min(100, Math.round((usage.runs_this_month / usage.runs_limit) * 100));
  }
  if (usage.installed_limit == null || usage.installed_limit <= 0) return 0;
  return Math.min(100, Math.round((usage.installed_count / usage.installed_limit) * 100));
}

type Props = {
  compact?: boolean;
};

export default function AgentAppUpgradeBanner({ compact = false }: Props) {
  const { data } = useSWR("agent-apps-usage", fetchAgentAppUsage);
  const usage = data?.usage;
  if (!usage) return null;

  const runsPct = usagePercent(usage, "runs");
  const installedPct = usagePercent(usage, "installed");
  const showRuns = usage.near_run_limit || runsPct >= 80;
  const showInstalled = installedPct >= 80;
  if (!showRuns && !showInstalled) return null;

  if (compact) {
    return (
      <Alert
        severity="warning"
        action={
          <Button component="a" href="/pricing" size="small" color="inherit">
            Upgrade
          </Button>
        }
      >
        Agent app usage is nearing your plan limit.
      </Alert>
    );
  }

  return (
    <Alert
      severity="warning"
      action={
        <Button component="a" href="/pricing" size="small" color="inherit">
          View plans
        </Button>
      }
    >
      <Stack spacing={1}>
        <Typography variant="subtitle2">Agent app usage</Typography>
        {showRuns && usage.runs_limit != null ? (
          <Box>
            <Typography variant="body2" color="text.secondary">
              Runs this month: {usage.runs_this_month} / {usage.runs_limit}
            </Typography>
            <LinearProgress variant="determinate" value={runsPct} sx={{ mt: 0.5 }} />
          </Box>
        ) : null}
        {showInstalled && usage.installed_limit != null ? (
          <Box>
            <Typography variant="body2" color="text.secondary">
              Installed apps: {usage.installed_count} / {usage.installed_limit}
            </Typography>
            <LinearProgress variant="determinate" value={installedPct} sx={{ mt: 0.5 }} />
          </Box>
        ) : null}
      </Stack>
    </Alert>
  );
}

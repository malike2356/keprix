"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { fetchAgentAppUsage } from "@/lib/agent-apps-api";

export default function AgentAppUsageCard() {
  const { data, isLoading } = useSWR("agent-apps-usage", fetchAgentAppUsage);
  const usage = data?.usage;

  return (
    <DashboardCard title="Agent Apps usage" subtitle="Install and run limits for your plan">
      {isLoading || !usage ? (
        <Typography variant="body2" color="text.secondary">
          Loading usage...
        </Typography>
      ) : (
        <Stack spacing={2}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Plan: {usage.plan}
            </Typography>
          </Box>
          <Box>
            <Typography variant="body2">
              Runs this month: {usage.runs_this_month}
              {usage.runs_limit != null ? ` / ${usage.runs_limit}` : " (unlimited)"}
            </Typography>
            {usage.runs_limit != null ? (
              <LinearProgress
                variant="determinate"
                value={Math.min(100, Math.round((usage.runs_this_month / usage.runs_limit) * 100))}
                sx={{ mt: 1 }}
              />
            ) : null}
          </Box>
          <Box>
            <Typography variant="body2">
              Installed apps: {usage.installed_count}
              {usage.installed_limit != null ? ` / ${usage.installed_limit}` : " (unlimited)"}
            </Typography>
          </Box>
          {usage.scheduled_limit != null ? (
            <Typography variant="body2" color="text.secondary">
              Scheduled apps: {usage.scheduled_count ?? 0} / {usage.scheduled_limit}
            </Typography>
          ) : null}
        </Stack>
      )}
    </DashboardCard>
  );
}

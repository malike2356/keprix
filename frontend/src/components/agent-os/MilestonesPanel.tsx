"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import { ceApi } from "@/lib/ce-api";

type Milestone = {
  id: string;
  day: number;
  title: string;
  copy: string;
  done: number;
  total: number;
  percent: number;
  complete: boolean;
  steps: Array<{ id: string; title: string; complete: boolean }>;
};

type MilestonesPayload = {
  ok: boolean;
  milestones: Milestone[];
  current?: { id: string };
};

async function fetchMilestones(): Promise<MilestonesPayload> {
  const response = await ceApi("/api/agent-os/milestones");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as MilestonesPayload;
}

export default function MilestonesPanel() {
  const { data, error, isLoading, mutate } = useSWR("agent-os-milestones", fetchMilestones);

  if (error) {
    return <ErrorState title="Could not load milestones" message={error.message} onRetry={() => void mutate()} />;
  }
  if (isLoading && !data) {
    return <LinearProgress sx={{ my: 2 }} />;
  }
  if (!data?.milestones?.length) {
    return (
      <EmptyState
        title="No milestones yet"
        description="Enable Agent OS and complete activation steps to track Day 1 / 7 / 30."
      />
    );
  }

  const currentId = data.current?.id;

  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, mb: 3 }}>
      {data.milestones.map((item) => (
        <Paper
          key={item.id}
          variant="outlined"
          sx={{
            p: 2,
            borderColor: currentId === item.id ? "primary.main" : "divider",
            borderWidth: currentId === item.id ? 2 : 1,
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              {item.title}
            </Typography>
            {item.complete ? <Chip size="small" color="success" label="Done" /> : null}
            {currentId === item.id && !item.complete ? <Chip size="small" color="primary" label="Current" /> : null}
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {item.copy}
          </Typography>
          <LinearProgress variant="determinate" value={item.percent} sx={{ mb: 1, height: 8, borderRadius: 1 }} />
          <Typography variant="caption" color="text.secondary">
            {item.done} / {item.total} steps ({item.percent}%)
          </Typography>
          <Stack spacing={0.5} sx={{ mt: 1.5 }}>
            {item.steps.map((step) => (
              <Typography
                key={step.id}
                variant="body2"
                sx={{ textDecoration: step.complete ? "line-through" : "none", opacity: step.complete ? 0.7 : 1 }}
              >
                {step.complete ? "[done]" : "[ ]"} {step.title}
              </Typography>
            ))}
          </Stack>
          <Button component="a" href="/agent-os/onboarding" size="small" sx={{ mt: 1 }}>
            Open checklist
          </Button>
        </Paper>
      ))}
    </Box>
  );
}

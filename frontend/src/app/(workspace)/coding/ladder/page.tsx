"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Metrics = {
  lines_not_written: number;
  files_not_created: number;
  dependencies_not_added: number;
  token_reduction_percent: number;
  cost_reduction_percent: number;
  time_reduction_percent: number;
};

async function fetchMetrics(): Promise<Metrics> {
  const response = await ceApi("/api/coding/ladder/metrics");
  if (!response.ok) throw new Error("Failed to load ladder metrics");
  return response.json();
}

export default function PonytailLadderPage() {
  const { data } = useSWR("ponytail-ladder-metrics", fetchMetrics);
  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <PageHeader title="Ponytail Ladder" description="Minimal-code guardrails, review, audit, debt, and effectiveness metrics." />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip label={`Lines not written: ${data?.lines_not_written ?? 0}`} />
          <Chip label={`Files avoided: ${data?.files_not_created ?? 0}`} />
          <Chip label={`Dependencies avoided: ${data?.dependencies_not_added ?? 0}`} />
        </Stack>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Savings</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip color="success" label={`Tokens -${data?.token_reduction_percent ?? 0}%`} />
          <Chip color="success" label={`Cost -${data?.cost_reduction_percent ?? 0}%`} />
          <Chip color="success" label={`Time -${data?.time_reduction_percent ?? 0}%`} />
        </Stack>
      </Paper>
    </Box>
  );
}

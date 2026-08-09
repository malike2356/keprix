"use client";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress"; // @loading-contract-ignore determinate metrics ring
import Typography from "@mui/material/Typography";
import type { CompoundingMetrics } from "@/lib/mutation-api";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock } from "@/components/ui/loading";

type CompoundingMetricsCardProps = {
  metrics?: CompoundingMetrics | null;
  loading?: boolean;
  compact?: boolean;
};

export default function CompoundingMetricsCard({
  metrics,
  loading = false,
  compact = false,
}: CompoundingMetricsCardProps) {
  const percent = Math.round((metrics?.divergence_score ?? 0) * 100);

  if (loading) {
    return (
      <DashboardCard title="Mutation divergence">
        <SkeletonBlock height={120} />
      </DashboardCard>
    );
  }

  return (
    <DashboardCard
      title="Mutation divergence"
      subtitle="Deployment-specific adaptation beyond base Keprix"
      action={
        compact ? undefined : (
          <Typography
            component="a"
            href="/dashboard/mutation"
            variant="body2"
            color="primary"
            sx={{ textDecoration: "none" }}
          >
            Full view
          </Typography>
        )
      }
    >
      <Box sx={{ display: "flex", gap: 3, alignItems: "center", flexWrap: "wrap" }}>
        <Box sx={{ position: "relative", display: "inline-flex" }}>
          <CircularProgress variant="determinate" value={percent} size={88} thickness={4} />
          <Box
            sx={{
              top: 0,
              left: 0,
              bottom: 0,
              right: 0,
              position: "absolute",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {percent}%
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: "grid", gap: 0.5 }}>
          <Typography variant="body2">
            Active mutations: <strong>{metrics?.active_mutations ?? 0}</strong>
          </Typography>
          <Typography variant="body2">
            Promoted tools: <strong>{metrics?.promoted_mutations ?? 0}</strong>
          </Typography>
          <Typography variant="body2">
            Prompt evolutions: <strong>{metrics?.prompts_evolved ?? 0}</strong>
          </Typography>
          <Typography variant="body2">
            Code merges: <strong>{metrics?.code_mutations_merged ?? 0}</strong>
          </Typography>
        </Box>
      </Box>
    </DashboardCard>
  );
}

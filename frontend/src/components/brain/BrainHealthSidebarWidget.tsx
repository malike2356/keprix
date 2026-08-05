"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { healthScoreColor } from "@/types/brain-health";
import { useBrainHealth } from "@/hooks/useBrainHealth";

export default function BrainHealthSidebarWidget() {
  const { report, loading } = useBrainHealth();
  const score = report?.health_score ?? 0;
  const color = healthScoreColor(score);

  return (
    <Box sx={{ px: 1, py: 1.5, borderTop: 1, borderColor: "divider" }}>
      <Stack
        component={Link}
        href="/brain/health"
        spacing={0.75}
        sx={{ textDecoration: "none", color: "inherit", px: 1.5 }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" color="text.secondary">Brain</Typography>
          <Typography variant="caption" sx={{ color, fontWeight: 700 }}>
            {loading && !report ? "..." : score}
          </Typography>
        </Stack>
        <LinearProgress
          variant={loading && !report ? "indeterminate" : "determinate"}
          value={score}
          sx={{
            height: 6,
            borderRadius: 999,
            bgcolor: "action.hover",
            "& .MuiLinearProgress-bar": { bgcolor: color },
          }}
        />
        <Typography variant="caption" color="text.secondary">
          View health
        </Typography>
      </Stack>
    </Box>
  );
}

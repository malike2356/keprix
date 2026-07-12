"use client";

import AssessmentIcon from "@mui/icons-material/Assessment";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HourglassTopIcon from "@mui/icons-material/HourglassTop";
import TokenIcon from "@mui/icons-material/Token";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

type Metrics = {
  token_burn_24h: number;
  runs_today: number;
  failed_runs: number;
  pending_approvals: number;
};

const items = [
  { key: "token_burn_24h", label: "Tokens 24h", icon: TokenIcon },
  { key: "runs_today", label: "Runs today", icon: AssessmentIcon },
  { key: "failed_runs", label: "Failed runs", icon: ErrorOutlineIcon },
  { key: "pending_approvals", label: "Approvals", icon: HourglassTopIcon },
] as const;

export default function ActionBoardMetrics({ metrics }: { metrics: Metrics }) {
  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" } }}>
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Paper key={item.key} variant="outlined" sx={{ p: 2, minHeight: 86 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
              <Icon fontSize="small" color="primary" />
              <Typography variant="caption" color="text.secondary">{item.label}</Typography>
            </Box>
            <Typography variant="h5">{Number(metrics[item.key] || 0).toLocaleString()}</Typography>
          </Paper>
        );
      })}
    </Box>
  );
}

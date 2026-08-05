"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { healthScoreColor } from "@/types/brain-health";

type Props = {
  score: number;
  label: string;
  generatedAt?: string;
  loading?: boolean;
  onRefresh?: () => void;
};

function minutesAgo(value?: string): string {
  if (!value) return "just now";
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(delta / 60000));
  if (minutes <= 0) return "just now";
  if (minutes === 1) return "1 min ago";
  return `${minutes} min ago`;
}

export default function BrainHealthScore({ score, label, generatedAt, loading = false, onRefresh }: Props) {
  const color = healthScoreColor(score);
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
        <Box>
          <Typography variant="h6">Brain Health Score: {score} / 100</Typography>
          <Chip size="small" label={label} sx={{ mt: 0.5, bgcolor: `${color}22`, color }} />
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Last checked: {minutesAgo(generatedAt)}
          </Typography>
          <Button size="small" variant="outlined" onClick={onRefresh} disabled={loading}>
            Refresh
          </Button>
        </Stack>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={score}
        sx={{
          mt: 1.5,
          height: 10,
          borderRadius: 999,
          bgcolor: "action.hover",
          "& .MuiLinearProgress-bar": { bgcolor: color },
        }}
      />
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";

type UsageMeterProps = {
  label: string;
  used: number;
  limit: number;
  unit?: string;
  loading?: boolean;
};

export default function UsageMeter({ label, used, limit, unit = "", loading = false }: UsageMeterProps) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const overLimit = used > limit;

  if (loading) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" color={overLimit ? "error.main" : "text.secondary"}>
          {used}{unit} / {limit}{unit}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={pct}
        color={overLimit ? "error" : pct > 80 ? "warning" : "primary"}
      />
    </Box>
  );
}

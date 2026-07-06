"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import dynamic from "next/dynamic";
import { useTheme } from "@mui/material/styles";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type MutationQualityBadgeProps = {
  score: number | null;
  useCount: number;
  status: string;
  samples?: number[];
};

function scoreColor(score: number | null, status: string): "default" | "success" | "warning" | "error" {
  if (score === null || status === "staged") return "default";
  if (score >= 0.75) return "success";
  if (score >= 0.45) return "warning";
  return "error";
}

export default function MutationQualityBadge({
  score,
  useCount,
  status,
  samples = [],
}: MutationQualityBadgeProps) {
  const theme = useTheme();
  const color = scoreColor(score, status);
  const label = score === null ? "N/A" : `${Math.round(score * 100)}%`;
  const barColor =
    color === "success"
      ? theme.palette.success.main
      : color === "warning"
        ? theme.palette.warning.main
        : color === "error"
          ? theme.palette.error.main
          : theme.palette.grey[500];

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 120 }}>
      <Chip size="small" label={label} color={color} variant={color === "default" ? "outlined" : "filled"} />
      <Box sx={{ flex: 1, minWidth: 60 }}>
        <Box
          sx={{
            height: 6,
            borderRadius: 1,
            bgcolor: "action.hover",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              width: `${Math.round((score ?? 0) * 100)}%`,
              height: "100%",
              bgcolor: barColor,
            }}
          />
        </Box>
        <Typography variant="caption" color="text.secondary">
          {useCount} uses
        </Typography>
      </Box>
      {samples.length >= 2 ? (
        <Box sx={{ width: 72 }}>
          <Chart
            type="line"
            height={32}
            width={72}
            series={[{ data: samples }]}
            options={{
              chart: { sparkline: { enabled: true }, animations: { enabled: false } },
              stroke: { width: 2, curve: "smooth" },
              colors: [barColor],
              tooltip: { enabled: false },
            }}
          />
        </Box>
      ) : null}
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";

type SkeletonChartProps = {
  height?: number;
};

export default function SkeletonChart({ height = 280 }: SkeletonChartProps) {
  return (
    <Box data-testid="skeleton-chart">
      <SkeletonBlock height={height} />
    </Box>
  );
}

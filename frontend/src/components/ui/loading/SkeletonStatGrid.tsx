"use client";

import Box from "@mui/material/Box";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";

type SkeletonStatGridProps = {
  count?: number;
};

export default function SkeletonStatGrid({ count = 4 }: SkeletonStatGridProps) {
  return (
    <Box
      data-testid="skeleton-stat-grid"
      sx={{
        display: "grid",
        gap: 2,
        gridTemplateColumns: {
          xs: "1fr",
          sm: "repeat(2, minmax(0, 1fr))",
          md: `repeat(${Math.min(count, 4)}, minmax(0, 1fr))`,
        },
      }}
    >
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonBlock key={index} height={120} />
      ))}
    </Box>
  );
}

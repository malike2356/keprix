"use client";

import Stack from "@mui/material/Stack";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";

type SkeletonListProps = {
  rows?: number;
  rowHeight?: number;
};

export default function SkeletonList({ rows = 5, rowHeight = 72 }: SkeletonListProps) {
  return (
    <Stack spacing={1.5} data-testid="skeleton-list">
      {Array.from({ length: rows }).map((_, index) => (
        <SkeletonBlock key={index} height={rowHeight} />
      ))}
    </Stack>
  );
}

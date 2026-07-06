"use client";

import Skeleton from "@mui/material/Skeleton";
import type { SxProps, Theme } from "@mui/material/styles";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

type SkeletonBlockProps = {
  height: number | string;
  width?: number | string;
  sx?: SxProps<Theme>;
};

export default function SkeletonBlock({ height, width, sx }: SkeletonBlockProps) {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <Skeleton
      variant="rounded"
      animation={reducedMotion ? false : "wave"}
      height={height}
      width={width ?? "100%"}
      sx={{ borderRadius: 1, ...sx }}
    />
  );
}

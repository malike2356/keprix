"use client";

import Stack from "@mui/material/Stack";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";

type SkeletonTextProps = {
  lines?: number;
};

export default function SkeletonText({ lines = 3 }: SkeletonTextProps) {
  return (
    <Stack spacing={1}>
      {Array.from({ length: lines }).map((_, index) => (
        <SkeletonBlock
          key={index}
          height={14}
          width={index === lines - 1 ? "72%" : "100%"}
        />
      ))}
    </Stack>
  );
}

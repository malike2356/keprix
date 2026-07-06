"use client";

import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import SkeletonBlock from "@/components/ui/loading/SkeletonBlock";
import SkeletonText from "@/components/ui/loading/SkeletonText";

type SkeletonDetailPanelProps = {
  fields?: number;
};

export default function SkeletonDetailPanel({ fields = 6 }: SkeletonDetailPanelProps) {
  return (
    <Box data-testid="skeleton-detail-panel" sx={{ display: "grid", gap: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "flex-start" }}>
        <Box sx={{ flex: 1 }}>
          <SkeletonBlock height={28} width="48%" sx={{ mb: 1 }} />
          <SkeletonBlock height={16} width="32%" />
        </Box>
        <SkeletonBlock height={24} width={88} />
      </Box>
      <Divider />
      <Stack spacing={1.5}>
        {Array.from({ length: fields }).map((_, index) => (
          <Box key={index}>
            <SkeletonBlock height={12} width="22%" sx={{ mb: 0.75 }} />
            <SkeletonText lines={index % 2 === 0 ? 2 : 1} />
          </Box>
        ))}
      </Stack>
      <Box sx={{ display: "flex", gap: 1 }}>
        <SkeletonBlock height={36} width={96} />
        <SkeletonBlock height={36} width={112} />
      </Box>
    </Box>
  );
}

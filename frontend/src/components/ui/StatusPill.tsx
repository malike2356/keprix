"use client";

import Chip from "@mui/material/Chip";
import { statusColors, statusLabels, type StatusKey } from "@/theme/tokens/status";

type StatusPillProps = {
  status: StatusKey;
  size?: "small" | "medium";
};

export default function StatusPill({ status, size = "small" }: StatusPillProps) {
  return (
    <Chip
      label={statusLabels[status]}
      color={statusColors[status]}
      size={size}
      variant="outlined"
    />
  );
}

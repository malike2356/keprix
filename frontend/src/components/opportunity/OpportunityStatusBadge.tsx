"use client";

import Chip from "@mui/material/Chip";

const STATUS_COLOR: Record<string, "default" | "info" | "warning" | "success" | "error" | "primary"> = {
  draft: "default",
  researching: "info",
  validating: "info",
  assets_ready: "primary",
  approval_required: "warning",
  launch_ready: "success",
  launched: "success",
  paused: "default",
  archived: "default",
};

type Props = {
  status: string;
  labels?: Record<string, string>;
};

export default function OpportunityStatusBadge({ status, labels }: Props) {
  const label = labels?.[status] ?? status.replace(/_/g, " ");
  return (
    <Chip
      size="small"
      label={label}
      color={STATUS_COLOR[status] ?? "default"}
      variant="outlined"
      sx={{ textTransform: "capitalize" }}
    />
  );
}

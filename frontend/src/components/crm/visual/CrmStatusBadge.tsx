"use client";

import Chip from "@mui/material/Chip";
import { RUNTIME_STATE_TONE, stateLabel } from "@/components/crm/visual/visual-contract";

type Props = {
  state: string | null | undefined;
  size?: "small" | "medium";
};

/** Colour is secondary; accessible text label is primary. */
export function CrmStatusBadge({ state, size = "small" }: Props) {
  const tone = RUNTIME_STATE_TONE[String(state || "")] || "default";
  const color =
    tone === "default" ? "default" : tone === "info" ? "info" : tone === "success" ? "success" : tone === "warning" ? "warning" : "error";
  return (
    <Chip
      size={size}
      color={color}
      variant={tone === "default" ? "outlined" : "filled"}
      label={stateLabel(state)}
      aria-label={`Status: ${stateLabel(state)}`}
    />
  );
}

export default CrmStatusBadge;

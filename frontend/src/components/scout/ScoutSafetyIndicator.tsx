"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import { IconShield } from "@tabler/icons-react";
import useSWR from "swr";
import { deriveGovernanceSafety } from "@/lib/governance-safety";
import { fetchGovernanceStatus } from "@/lib/governance-api";

const ICON_COLORS: Record<string, string> = {
  loading: "text.secondary",
  unknown: "text.secondary",
  self_governed: "info.main",
  ungoverned: "warning.main",
  governed: "success.main",
  degraded: "warning.main",
  kill_active: "error.main",
};

type ScoutSafetyIndicatorProps = {
  showLabel?: boolean;
};

export default function ScoutSafetyIndicator({ showLabel = true }: ScoutSafetyIndicatorProps) {
  const { data, error, isLoading } = useSWR("governance-status", fetchGovernanceStatus, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });

  const view = deriveGovernanceSafety(error ? undefined : data, isLoading);
  const iconColor = ICON_COLORS[view.level] || "text.secondary";

  return (
    <Tooltip title={view.tooltip}>
      <Box
        component="a"
        href="/settings/governance"
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.5,
          color: "inherit",
          textDecoration: "none",
          borderRadius: 1,
          "&:hover": { bgcolor: "action.hover" },
        }}
        aria-label={`Governance safety: ${view.label}. ${view.tooltip}`}
      >
        <IconButton
          component="span"
          color="inherit"
          size="small"
          tabIndex={-1}
          sx={{ pointerEvents: "none", color: iconColor }}
        >
          <IconShield size={18} stroke={1.75} />
        </IconButton>
        {showLabel ? (
          <Chip
            component="span"
            label={view.label}
            size="small"
            color={view.chipColor}
            variant="outlined"
            sx={{ pointerEvents: "none", display: { xs: "none", sm: "inline-flex" } }}
          />
        ) : null}
      </Box>
    </Tooltip>
  );
}

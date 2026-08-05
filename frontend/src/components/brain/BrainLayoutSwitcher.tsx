"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonGroup from "@mui/material/ButtonGroup";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import { LAYOUT_REGISTRY } from "@/lib/brain/layout-registry";
import type { LayoutMode } from "@/lib/brain/layout-types";
import { brainGlassSx } from "@/components/brain/brain-surface";

type Props = {
  mode: LayoutMode;
  onModeChange: (mode: LayoutMode) => void;
  clustersEnabled: boolean;
  onClustersChange: (enabled: boolean) => void;
  busy?: boolean;
  /** When true, skip absolute positioning (parent provides chrome). */
  embedded?: boolean;
};

export default function BrainLayoutSwitcher({
  mode,
  onModeChange,
  clustersEnabled,
  onClustersChange,
  busy = false,
  embedded = false,
}: Props) {
  return (
    <Box
      sx={
        embedded
          ? { p: 0 }
          : {
              ...brainGlassSx,
              position: "absolute",
              top: 12,
              right: 12,
              zIndex: 5,
              p: 0.75,
            }
      }
    >
      <Stack direction="row" spacing={1} alignItems="center">
        <ButtonGroup
          size="small"
          variant="outlined"
          disabled={busy}
          sx={{
            "& .MuiButton-root": {
              textTransform: "none",
              fontWeight: 500,
              px: 1.25,
              borderColor: "divider",
              color: "text.secondary",
            },
            "& .MuiButton-contained": {
              bgcolor: "action.selected",
              color: "text.primary",
              borderColor: "divider",
              boxShadow: "none",
              "&:hover": { bgcolor: "action.selected", boxShadow: "none" },
            },
          }}
        >
          {LAYOUT_REGISTRY.map((layout) => (
            <Button
              key={layout.id}
              variant={mode === layout.id ? "contained" : "outlined"}
              onClick={() => onModeChange(layout.id)}
            >
              {layout.label}
            </Button>
          ))}
        </ButtonGroup>
        <Stack direction="row" spacing={0.25} alignItems="center" sx={{ pl: 0.25 }}>
          <Switch
            size="small"
            checked={clustersEnabled}
            onChange={(_, checked) => onClustersChange(checked)}
            inputProps={{ "aria-label": "Toggle cluster bubbles" }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ pr: 0.5 }}>
            Clusters
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}

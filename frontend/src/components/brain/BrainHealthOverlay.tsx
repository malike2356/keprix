"use client";

import Switch from "@mui/material/Switch";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type Props = {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
};

export default function BrainHealthOverlay({ enabled, onChange }: Props) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <Switch
        size="small"
        checked={enabled}
        onChange={(_, checked) => onChange(checked)}
        inputProps={{ "aria-label": "Toggle health overlay" }}
      />
      <Typography variant="caption" color="text.secondary">
        Health overlay
      </Typography>
    </Stack>
  );
}

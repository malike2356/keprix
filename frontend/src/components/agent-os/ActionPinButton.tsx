"use client";

import EventRepeatIcon from "@mui/icons-material/EventRepeat";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

export type ActionPin = {
  pin_id: string;
  type: "skill" | "playbook" | "agent_app";
  id: string;
  label: string;
  shortcut?: string | null;
};

export default function ActionPinButton({
  pin,
  running,
  onRun,
  onSchedule,
}: {
  pin: ActionPin;
  running: boolean;
  onRun: (pin: ActionPin) => void;
  onSchedule: (pin: ActionPin) => void;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 1.5, minHeight: 150 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
        <Box>
          <Typography variant="subtitle1">{pin.label}</Typography>
          <Typography variant="caption" color="text.secondary">{pin.type}: {pin.id}</Typography>
        </Box>
        {pin.shortcut ? <Chip size="small" label={pin.shortcut} /> : null}
      </Box>
      <Box sx={{ display: "flex", gap: 1, mt: "auto", flexWrap: "wrap" }}>
        <Button size="small" variant="contained" startIcon={<PlayArrowIcon />} disabled={running} onClick={() => onRun(pin)}>
          {running ? "Running" : "Run"}
        </Button>
        {pin.type === "skill" ? (
          <Button size="small" variant="outlined" startIcon={<EventRepeatIcon />} onClick={() => onSchedule(pin)}>
            Schedule
          </Button>
        ) : null}
      </Box>
    </Paper>
  );
}

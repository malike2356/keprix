"use client";

import EventRepeatIcon from "@mui/icons-material/EventRepeat";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import * as React from "react";
import { ceApi } from "@/lib/ce-api";

export default function ActionScheduleDialog({
  skillSlug,
  open,
  onClose,
  onScheduled,
}: {
  skillSlug: string | null;
  open: boolean;
  onClose: () => void;
  onScheduled: (message: string) => void;
}) {
  const [schedule, setSchedule] = React.useState("0 8 * * 1-5");
  const [busy, setBusy] = React.useState(false);

  const submit = async () => {
    if (!skillSlug) return;
    setBusy(true);
    try {
      const response = await ceApi("/api/agent-os/board/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_slug: skillSlug, schedule, name: skillSlug }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { id: string };
      onScheduled(`Scheduled ${skillSlug}: ${payload.id}`);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Schedule action</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
        <TextField label="Skill" value={skillSlug || ""} disabled />
        <TextField label="Schedule" value={schedule} onChange={(event) => setSchedule(event.target.value)} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button disabled={busy || !skillSlug} variant="contained" startIcon={<EventRepeatIcon />} onClick={() => void submit()}>
          Schedule
        </Button>
      </DialogActions>
    </Dialog>
  );
}

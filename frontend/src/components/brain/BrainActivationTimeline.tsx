"use client";

import DownloadIcon from "@mui/icons-material/Download";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { BrainActivationEvent } from "@/types/brain-graph";

export default function BrainActivationTimeline({ sessionId, events, paused, onPause, onClear }: { sessionId: string | null; events: BrainActivationEvent[]; paused: boolean; onPause: (paused: boolean) => void; onClear: () => void }) {
  const exportLog = () => {
    const text = events.map((event) => `${event.ts} ${event.node_kind} ${event.node_id} ${event.relation || event.type}`).join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "brain-activation.log";
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Paper variant="outlined" sx={{ maxHeight: 180, overflow: "auto" }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ px: 1, py: 0.75, borderBottom: 1, borderColor: "divider" }}>
        <Typography variant="subtitle2" sx={{ flex: 1 }}>Brain Activity</Typography>
        <Chip size="small" color={sessionId && !paused ? "success" : "default"} label={sessionId ? `${paused ? "Paused" : "Live"}: ${sessionId}` : "No live session"} />
        <Button size="small" startIcon={paused ? <PlayArrowIcon /> : <PauseIcon />} onClick={() => onPause(!paused)} disabled={!sessionId}>{paused ? "Resume" : "Pause"}</Button>
        <Button size="small" onClick={onClear}>Clear</Button>
        <Button size="small" startIcon={<DownloadIcon />} onClick={exportLog}>Export</Button>
      </Stack>
      <Box sx={{ px: 1, py: 0.5 }}>
        {events.length === 0 ? <Typography variant="body2" color="text.secondary">Waiting for activation events.</Typography> : null}
        {events.map((event, index) => (
          <Stack key={`${event.ts}-${index}`} direction="row" spacing={1} alignItems="center" sx={{ py: 0.35 }}>
            <Typography variant="caption" sx={{ width: 70 }}>{new Date(event.ts).toLocaleTimeString()}</Typography>
            <Chip size="small" label={event.node_kind} />
            <Typography variant="body2" sx={{ flex: 1 }} noWrap>{event.node_id}</Typography>
            <Typography variant="caption" color="text.secondary">{event.relation || event.type}</Typography>
            {event.confidence != null ? <Typography variant="caption">conf {event.confidence.toFixed(2)}</Typography> : null}
          </Stack>
        ))}
      </Box>
    </Paper>
  );
}

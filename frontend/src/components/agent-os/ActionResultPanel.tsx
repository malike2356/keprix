"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import StructuredDataView from "@/components/ui/StructuredDataView";

export type HeadlessRun = {
  run_id: string;
  source_type: string;
  source_id: string;
  status: string;
  output: Record<string, unknown>;
  error?: string | null;
  ledger_entry_id?: string | null;
  duration_ms: number;
  events: Array<{ event: string; payload: Record<string, unknown>; created_at: string }>;
};

export default function ActionResultPanel({ run, onRunAgain }: { run: HeadlessRun | null; onRunAgain: () => void }) {
  if (!run) return null;
  return (
    <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
        <Box>
          <Typography variant="subtitle1">{run.source_id}</Typography>
          <Typography variant="caption" color="text.secondary">{run.run_id}</Typography>
        </Box>
        <Chip size="small" label={run.status} color={run.status === "failed" ? "error" : "success"} />
      </Box>
      {run.error ? <Alert severity="error">{run.error}</Alert> : null}
      <Typography variant="body2" color="text.secondary">
        Duration: {run.duration_ms} ms {run.ledger_entry_id ? `| Ledger: ${run.ledger_entry_id}` : ""}
      </Typography>
      <Box sx={{ p: 2, bgcolor: "action.hover", overflow: "auto", maxHeight: 240 }}>
        <StructuredDataView value={run.output} emptyLabel="No output" />
      </Box>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button size="small" variant="outlined" href={`/agent-os/runs?source_type=${run.source_type}&source_id=${encodeURIComponent(run.source_id)}&run_id=${encodeURIComponent(run.run_id)}`}>
          View ledger
        </Button>
        <Button size="small" onClick={onRunAgain}>
          Run again
        </Button>
      </Box>
    </Paper>
  );
}

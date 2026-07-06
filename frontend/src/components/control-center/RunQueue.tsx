"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { QueueRun } from "@/lib/control-center-api";

type RunQueueProps = {
  queued: QueueRun[];
  failed: QueueRun[];
};

function statusColor(status: string): "success" | "warning" | "error" | "default" {
  if (status === "completed") return "success";
  if (status === "queued" || status === "running") return "warning";
  if (status === "failed") return "error";
  return "default";
}

export default function RunQueue({ queued, failed }: RunQueueProps) {
  const rows = [...queued, ...failed];
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 2 }}>
          Run queue
        </Typography>
        {rows.length === 0 ? (
          <Typography variant="body2">No queued or failed runs.</Typography>
        ) : (
          rows.map((run) => (
            <Box key={run.id} sx={{ mb: 1.5 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {run.id.slice(0, 8)}
                </Typography>
                <Chip size="small" color={statusColor(run.status)} label={run.status} />
              </Box>
              {run.logs?.length ? (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {run.logs[run.logs.length - 1]}
                </Typography>
              ) : null}
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
}

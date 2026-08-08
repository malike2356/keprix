"use client";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  groupPlaybookEventsByNode,
  redactStateForDisplay,
  type PlaybookEvent,
  type StepRunRow,
  type StepRunStatus,
} from "@/lib/playbook-api";

type PlaybookStepTimelineProps = {
  events: PlaybookEvent[];
};

function statusChipColor(
  status: StepRunStatus,
): "default" | "success" | "warning" | "error" | "info" {
  if (status === "success") return "success";
  if (status === "failed") return "error";
  if (status === "interrupted") return "warning";
  if (status === "running") return "info";
  return "default";
}

function formatDuration(durationMs?: number): string | null {
  if (durationMs === undefined) return null;
  if (durationMs < 1000) return `${durationMs} ms`;
  return `${(durationMs / 1000).toFixed(2)} s`;
}

function StatePanel({ value }: { value: Record<string, unknown> | undefined }) {
  const display = redactStateForDisplay(value) ?? {};
  return <StructuredDataView value={display} />;
}

function StepRow({ row }: { row: StepRunRow }) {
  const [open, setOpen] = React.useState(false);
  const [tab, setTab] = React.useState(0);
  const duration = formatDuration(row.duration_ms);

  const copyJson = async (payload: Record<string, unknown> | undefined) => {
    const display = redactStateForDisplay(payload) ?? {};
    await navigator.clipboard.writeText(JSON.stringify(display, null, 2));
  };

  return (
    <Box
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        py: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
        <IconButton size="small" aria-label="Expand step" onClick={() => setOpen((value) => !value)}>
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
        <Typography variant="subtitle2" sx={{ flex: 1 }}>
          {row.node}
        </Typography>
        <Chip size="small" color={statusChipColor(row.status)} label={row.status} />
        {duration ? <Chip size="small" variant="outlined" label={duration} /> : null}
      </Box>
      {row.error ? (
        <Alert severity={row.status === "failed" ? "error" : "warning"} sx={{ mt: 1 }}>
          {row.error}
        </Alert>
      ) : null}
      {open ? (
        <Box sx={{ mt: 1.5 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Tabs value={tab} onChange={(_, value) => setTab(value)}>
              <Tab label="Input" />
              <Tab label="Output" />
              <Tab label="Events" />
            </Tabs>
            <IconButton
              size="small"
              aria-label="Copy data"
              onClick={() =>
                void copyJson(
                  tab === 0
                    ? row.input_state
                    : tab === 1
                      ? row.output_state
                      : ({ events: row.rawEvents } as Record<string, unknown>),
                )
              }
            >
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Box>
          {tab === 0 ? <StatePanel value={row.input_state} /> : null}
          {tab === 1 ? <StatePanel value={row.output_state} /> : null}
          {tab === 2 ? <StructuredDataView value={row.rawEvents} /> : null}
        </Box>
      ) : null}
    </Box>
  );
}

export default function PlaybookStepTimeline({ events }: PlaybookStepTimelineProps) {
  const rows = React.useMemo(() => groupPlaybookEventsByNode(events), [events]);

  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No step executions yet.
      </Typography>
    );
  }

  return (
    <Box>
      {rows.map((row) => (
        <StepRow key={row.node} row={row} />
      ))}
    </Box>
  );
}

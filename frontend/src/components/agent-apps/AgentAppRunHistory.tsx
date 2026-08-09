"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import ReplayIcon from "@mui/icons-material/Replay";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  fetchAgentAppRun,
  fetchAgentAppRuns,
  type AgentAppLifecycleEvent,
  type AgentAppRunSummary,
} from "@/lib/agent-apps-api";

function statusColor(status: string): "success" | "error" | "warning" | "default" {
  if (status === "success") return "success";
  if (status === "error") return "error";
  if (status === "running") return "warning";
  return "default";
}

function formatTimeAgo(iso: string) {
  const delta = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function EventTimeline({ events }: { events: AgentAppLifecycleEvent[] }) {
  if (!events.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No lifecycle events recorded for this run.
      </Typography>
    );
  }
  return (
    <Stack spacing={1.5}>
      {events.map((item, index) => (
        <Box
          key={`${item.event}-${item.created_at}-${index}`}
          sx={{
            borderLeft: 2,
            borderColor: "divider",
            pl: 2,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            {new Date(item.created_at).toLocaleString()}
          </Typography>
          <Typography variant="subtitle2">{item.event}</Typography>
          <StructuredDataView value={item.payload} emptyLabel="-" />
        </Box>
      ))}
    </Stack>
  );
}

type Props = {
  appName: string;
  onRerun?: (run: AgentAppRunSummary) => void;
};

export default function AgentAppRunHistory({ appName, onRerun }: Props) {
  const { data, isLoading, mutate } = useSWR(["agent-app-runs", appName], () => fetchAgentAppRuns(appName));
  const [selectedTraceId, setSelectedTraceId] = React.useState<string | null>(null);
  const { data: detail } = useSWR(
    selectedTraceId ? ["agent-app-run", selectedTraceId] : null,
    () => fetchAgentAppRun(selectedTraceId as string),
  );

  const runs = data?.runs ?? [];

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="subtitle1">Run history</Typography>
        <Button size="small" onClick={() => mutate()}>
          Refresh
        </Button>
      </Stack>

      {isLoading ? <Typography variant="body2">Loading runs...</Typography> : null}
      {!isLoading && runs.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No runs yet. Use the Run tab to execute this app.
        </Typography>
      ) : null}

      {runs.length > 0 ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Status</TableCell>
              <TableCell>When</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Input</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.trace_id} hover>
                <TableCell>
                  <Chip size="small" label={run.status} color={statusColor(run.status)} />
                </TableCell>
                <TableCell>{formatTimeAgo(run.started_at)}</TableCell>
                <TableCell>{run.duration_ms != null ? `${run.duration_ms} ms` : "-"}</TableCell>
                <TableCell sx={{ maxWidth: 240 }}>
                  <Typography variant="body2" noWrap title={run.input_preview}>
                    {run.input_preview || "-"}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button size="small" onClick={() => setSelectedTraceId(run.trace_id)}>
                      View
                    </Button>
                    {onRerun ? (
                      <Button size="small" startIcon={<ReplayIcon />} onClick={() => onRerun(run)}>
                        Re-run
                      </Button>
                    ) : null}
                    <Button
                      size="small"
                      component="a"
                      href={`/agent-runtime?source=agent_app&app=${encodeURIComponent(appName)}&trace_id=${encodeURIComponent(run.trace_id)}`}
                      startIcon={<OpenInNewIcon />}
                    >
                      Runtime
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}

      <Drawer anchor="right" open={Boolean(selectedTraceId)} onClose={() => setSelectedTraceId(null)}>
        <Box sx={{ width: { xs: "100vw", sm: 420 }, p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="h6">Run trace</Typography>
            <IconButton onClick={() => setSelectedTraceId(null)} aria-label="Close trace drawer">
              <CloseIcon />
            </IconButton>
          </Stack>
          {detail?.run ? (
            <Stack spacing={2}>
              <Box>
                <Chip size="small" label={detail.run.status} color={statusColor(detail.run.status)} sx={{ mr: 1 }} />
                <Typography variant="caption" color="text.secondary">
                  {detail.run.trace_id}
                </Typography>
              </Box>
              {detail.run.error ? <Typography color="error">{detail.run.error}</Typography> : null}
              <EventTimeline events={detail.events} />
            </Stack>
          ) : (
            <Typography variant="body2">Loading trace...</Typography>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}

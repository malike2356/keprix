"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MenuItem from "@mui/material/MenuItem";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";

type TrajectoryRow = {
  trajectory_id: string;
  title?: string;
  workspace_id?: string;
  updated_at?: string;
  parent_trajectory_id?: string | null;
};

type TrajectoryEvent = {
  event_id: string;
  seq: number;
  event_type: string;
  timestamp: string;
  tool_name?: string | null;
  soft_wall_outcome?: string | null;
  error_text?: string | null;
  payload?: Record<string, unknown>;
};

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export default function TrajectoryPage() {
  const [list, setList] = React.useState<TrajectoryRow[]>([]);
  const [selectedId, setSelectedId] = React.useState<string>("");
  const [events, setEvents] = React.useState<TrajectoryEvent[]>([]);
  const [detail, setDetail] = React.useState<TrajectoryEvent | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [eventType, setEventType] = React.useState("");
  const [toolName, setToolName] = React.useState("");
  const [softWall, setSoftWall] = React.useState("");
  const [errorQuery, setErrorQuery] = React.useState("");
  const [forkSeq, setForkSeq] = React.useState("1");
  const [busy, setBusy] = React.useState(false);

  const refreshList = React.useCallback(async () => {
    setError(null);
    try {
      const data = await apiGet<{ trajectories: TrajectoryRow[] }>("/api/trajectories");
      setList(data.trajectories || []);
      if (!selectedId && data.trajectories?.length) {
        setSelectedId(data.trajectories[0].trajectory_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [selectedId]);

  const loadTrajectory = React.useCallback(async (id: string) => {
    if (!id) {
      setEvents([]);
      return;
    }
    setError(null);
    try {
      const data = await apiGet<{ events: TrajectoryEvent[] }>(`/api/trajectories/${encodeURIComponent(id)}`);
      setEvents(data.events || []);
      setDetail(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  React.useEffect(() => {
    void refreshList();
  }, [refreshList]);

  React.useEffect(() => {
    void loadTrajectory(selectedId);
  }, [selectedId, loadTrajectory]);

  const onSearch = async () => {
    setBusy(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedId) params.set("trajectory_id", selectedId);
      if (eventType) params.set("event_type", eventType);
      if (toolName) params.set("tool_name", toolName);
      if (softWall) params.set("soft_wall_outcome", softWall);
      if (errorQuery) params.set("error_query", errorQuery);
      const data = await apiGet<{ events: TrajectoryEvent[] }>(`/api/trajectories/search?${params}`);
      setEvents(data.events || []);
      setMessage(`Search returned ${data.events?.length ?? 0} event(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const onFork = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const seq = Number(forkSeq) || 0;
      const child = await apiPost<{ trajectory_id: string; forked_event_count: number }>(
        `/api/trajectories/${encodeURIComponent(selectedId)}/fork`,
        { through_seq: seq },
      );
      setMessage(`Forked to ${child.trajectory_id} (${child.forked_event_count} events).`);
      await refreshList();
      setSelectedId(child.trajectory_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const onReplay = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await apiPost<{ step_count: number; mode: string }>(
        `/api/trajectories/${encodeURIComponent(selectedId)}/replay`,
        { mode: "recorded", from_seq: 1 },
      );
      setMessage(`Recorded replay prepared: ${result.step_count} step(s), mode=${result.mode}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await apiPost<TrajectoryRow>("/api/trajectories", {
        title: "Operator trajectory",
      });
      setMessage(`Created ${created.trajectory_id}`);
      await refreshList();
      setSelectedId(created.trajectory_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ p: 2, maxWidth: 1200, mx: "auto" }} data-testid="trajectory-page">
      <PageHeader
        title="Session trajectory"
        subtitle="Append-only event log for Soft Wall, mutations, tools, and fork/replay debugging."
      />
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 2 }}>
        <Box sx={{ width: { xs: "100%", md: 280 }, flexShrink: 0 }}>
          <Stack spacing={1}>
            <Button variant="contained" onClick={() => void onCreate()} disabled={busy}>
              New trajectory
            </Button>
            <Button variant="outlined" onClick={() => void refreshList()} disabled={busy}>
              Refresh
            </Button>
            <TextField
              select
              label="Trajectory"
              size="small"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              fullWidth
            >
              {list.map((row) => (
                <MenuItem key={row.trajectory_id} value={row.trajectory_id}>
                  {row.title || row.trajectory_id.slice(0, 8)}
                </MenuItem>
              ))}
            </TextField>
            {!list.length ? (
              <Typography variant="body2" color="text.secondary">
                No trajectories yet. Create one to start logging Soft Wall and tool events.
              </Typography>
            ) : null}
          </Stack>
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
            <TextField
              label="Event type"
              size="small"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              placeholder="soft_wall"
            />
            <TextField
              label="Tool"
              size="small"
              value={toolName}
              onChange={(e) => setToolName(e.target.value)}
              placeholder="terminal"
            />
            <TextField
              label="Soft Wall"
              size="small"
              value={softWall}
              onChange={(e) => setSoftWall(e.target.value)}
              placeholder="denied"
            />
            <TextField
              label="Error text"
              size="small"
              value={errorQuery}
              onChange={(e) => setErrorQuery(e.target.value)}
            />
            <Button variant="outlined" onClick={() => void onSearch()} disabled={busy}>
              Search
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
            <TextField
              label="Fork through seq"
              size="small"
              value={forkSeq}
              onChange={(e) => setForkSeq(e.target.value)}
              sx={{ width: 140 }}
            />
            <Button variant="outlined" onClick={() => void onFork()} disabled={busy || !selectedId}>
              Fork
            </Button>
            <Button variant="outlined" onClick={() => void onReplay()} disabled={busy || !selectedId}>
              Replay (recorded)
            </Button>
          </Stack>
          {message ? (
            <Typography variant="body2" color="success.main" sx={{ mb: 1 }}>
              {message}
            </Typography>
          ) : null}
          {error ? (
            <Typography variant="body2" color="error" sx={{ mb: 1 }}>
              {error}
            </Typography>
          ) : null}
          <Stack spacing={1}>
            {events.map((ev) => (
              <Box
                key={ev.event_id}
                onClick={() => setDetail(ev)}
                sx={{
                  border: "1px solid",
                  borderColor: detail?.event_id === ev.event_id ? "primary.main" : "divider",
                  borderRadius: 1,
                  p: 1.5,
                  cursor: "pointer",
                }}
                data-testid={`trajectory-event-${ev.seq}`}
              >
                <Typography variant="subtitle2">
                  #{ev.seq} {ev.event_type}
                  {ev.tool_name ? ` · ${ev.tool_name}` : ""}
                  {ev.soft_wall_outcome ? ` · Soft Wall ${ev.soft_wall_outcome}` : ""}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {ev.timestamp}
                  {ev.error_text ? ` · ${ev.error_text}` : ""}
                </Typography>
              </Box>
            ))}
            {!events.length ? (
              <Typography variant="body2" color="text.secondary">
                No events in this view.
              </Typography>
            ) : null}
          </Stack>
          {detail ? (
            <Box sx={{ mt: 2, p: 2, bgcolor: "action.hover", borderRadius: 1 }}>
              <Typography variant="subtitle2">Event detail</Typography>
              <Typography
                component="pre"
                variant="body2"
                sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word", m: 0 }}
              >
                {JSON.stringify(detail, null, 2)}
              </Typography>
            </Box>
          ) : null}
        </Box>
      </Stack>
    </Box>
  );
}

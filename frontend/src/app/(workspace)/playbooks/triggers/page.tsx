"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Trigger = {
  id: string;
  name: string;
  kind: string;
  enabled: boolean;
  schedule?: { type?: string; every_minutes?: number; at_hour?: number; at_minute?: number } | null;
  event?: { source?: string; event_type?: string } | null;
  action: { type: string; config?: Record<string, unknown> };
  approval_mode: string;
  ai_mode: string;
  next_run_at?: string | null;
  last_run_at?: string | null;
};

type TriggerRun = {
  id: string;
  trigger_id: string;
  status: string;
  created_at: string;
  finished_at?: string | null;
  approval_id?: string | null;
  ledger_entry_id?: string | null;
  result?: Record<string, unknown>;
};

async function fetchTriggers() {
  const response = await ceApi("/api/triggers");
  if (!response.ok) throw new Error("Failed to load triggers");
  return (await response.json()) as { triggers: Trigger[] };
}

async function fetchRuns() {
  const response = await ceApi("/api/triggers/runs?limit=40");
  if (!response.ok) throw new Error("Failed to load runs");
  return (await response.json()) as { runs: TriggerRun[] };
}

export default function PlaybookTriggersPage() {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("Morning digest");
  const [scheduleType, setScheduleType] = useState("daily");
  const [everyMinutes, setEveryMinutes] = useState("30");
  const [atHour, setAtHour] = useState("7");
  const [atMinute, setAtMinute] = useState("0");
  const [actionType, setActionType] = useState("run_playbook");
  const [playbookId, setPlaybookId] = useState("");
  const [prompt, setPrompt] = useState("Summarize unread workspace activity");
  const [approvalMode, setApprovalMode] = useState("auto");
  const [aiMode, setAiMode] = useState("managed");

  const { data, mutate, isLoading } = useSWR("playbook-triggers", fetchTriggers);
  const { data: runsData, mutate: mutateRuns } = useSWR("playbook-trigger-runs", fetchRuns);

  const buildSchedule = () => {
    if (scheduleType === "interval") {
      return { type: "interval", every_minutes: Number(everyMinutes) || 30 };
    }
    if (scheduleType === "weekly") {
      return { type: "weekly", weekday: 1, at_hour: Number(atHour) || 9, at_minute: Number(atMinute) || 0 };
    }
    if (scheduleType === "monthly") {
      return { type: "monthly", day: 1, at_hour: Number(atHour) || 8, at_minute: Number(atMinute) || 0 };
    }
    if (scheduleType === "cron") {
      return { type: "cron", cron: "0 7 * * *" };
    }
    return { type: "daily", at_hour: Number(atHour) || 7, at_minute: Number(atMinute) || 0 };
  };

  const buildAction = () => {
    if (actionType === "ask_agent") {
      return { type: "ask_agent", config: { prompt } };
    }
    if (actionType === "call_tool") {
      return { type: "call_tool", config: { tool_name: "web_search", args: { query: prompt } } };
    }
    if (actionType === "create_task") {
      return { type: "create_task", config: { title: name } };
    }
    return { type: "run_playbook", config: { playbook_id: playbookId || "example" } };
  };

  const createTrigger = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi("/api/triggers", {
        method: "POST",
        body: JSON.stringify({
          name,
          kind: "schedule",
          schedule: buildSchedule(),
          action: buildAction(),
          approval_mode: approvalMode,
          ai_mode: aiMode,
          timezone: "UTC",
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Failed to create trigger");
      }
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create trigger");
    } finally {
      setBusy(false);
    }
  };

  const testTrigger = async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi(`/api/triggers/${id}/test`, { method: "POST" });
      if (!response.ok) throw new Error("Test run failed");
      await mutateRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test run failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleEnabled = async (trigger: Trigger) => {
    setBusy(true);
    try {
      await ceApi(`/api/triggers/${trigger.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !trigger.enabled }),
      });
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const approveRun = async (runId: string) => {
    setBusy(true);
    try {
      const response = await ceApi(`/api/triggers/runs/${runId}/approve`, { method: "POST" });
      if (!response.ok) throw new Error("Approve failed");
      await mutateRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const runTick = async () => {
    setBusy(true);
    try {
      await ceApi("/api/triggers/tick", { method: "POST" });
      await mutate();
      await mutateRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tick failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <PageHeader
        title="Trigger builder"
        description="When this happens, run a playbook, ask an agent, or call a tool. No cron config required."
        actions={
          <Button variant="outlined" disabled={busy} onClick={() => void runTick()}>
            Run scheduler tick
          </Button>
        }
      />

      {error ? <Alert severity="error">{error}</Alert> : null}

      <DashboardCard title="Create schedule trigger" subtitle="Interval, daily, weekly, monthly, or cron">
        <Stack spacing={2}>
          <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField select size="small" label="Schedule" value={scheduleType} onChange={(e) => setScheduleType(e.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="interval">Every N minutes</MenuItem>
              <MenuItem value="daily">Daily</MenuItem>
              <MenuItem value="weekly">Weekly</MenuItem>
              <MenuItem value="monthly">Monthly</MenuItem>
              <MenuItem value="cron">Cron (advanced)</MenuItem>
            </TextField>
            {scheduleType === "interval" ? (
              <TextField size="small" label="Minutes" value={everyMinutes} onChange={(e) => setEveryMinutes(e.target.value)} sx={{ width: 120 }} />
            ) : (
              <>
                <TextField size="small" label="Hour" value={atHour} onChange={(e) => setAtHour(e.target.value)} sx={{ width: 100 }} />
                <TextField size="small" label="Minute" value={atMinute} onChange={(e) => setAtMinute(e.target.value)} sx={{ width: 100 }} />
              </>
            )}
            <TextField select size="small" label="Action" value={actionType} onChange={(e) => setActionType(e.target.value)} sx={{ minWidth: 160 }}>
              <MenuItem value="run_playbook">Run playbook</MenuItem>
              <MenuItem value="ask_agent">Ask agent</MenuItem>
              <MenuItem value="call_tool">Call tool</MenuItem>
              <MenuItem value="create_task">Create task</MenuItem>
            </TextField>
            <TextField select size="small" label="Approval" value={approvalMode} onChange={(e) => setApprovalMode(e.target.value)} sx={{ minWidth: 140 }}>
              <MenuItem value="auto">Auto (risky waits)</MenuItem>
              <MenuItem value="required">Always approve</MenuItem>
              <MenuItem value="notify">Notify only</MenuItem>
            </TextField>
            <TextField select size="small" label="AI mode" value={aiMode} onChange={(e) => setAiMode(e.target.value)} sx={{ minWidth: 140 }}>
              <MenuItem value="managed">Managed wallet</MenuItem>
              <MenuItem value="byok">BYOK</MenuItem>
            </TextField>
          </Stack>
          {actionType === "run_playbook" ? (
            <TextField size="small" label="Playbook ID" value={playbookId} onChange={(e) => setPlaybookId(e.target.value)} fullWidth />
          ) : (
            <TextField size="small" label="Prompt / query" value={prompt} onChange={(e) => setPrompt(e.target.value)} fullWidth />
          )}
          <Button variant="contained" disabled={busy || !name.trim()} onClick={() => void createTrigger()} sx={{ alignSelf: "flex-start" }}>
            Create trigger
          </Button>
        </Stack>
      </DashboardCard>

      <DashboardCard title="Your triggers" subtitle={isLoading ? "Loading…" : `${data?.triggers.length ?? 0} configured`}>
        {(data?.triggers || []).length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No triggers yet. Create one above, or promote a playbook schedule from Agent OS.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>When</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Next</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(data?.triggers || []).map((trigger) => (
                <TableRow key={trigger.id}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {trigger.name}
                    </Typography>
                    <Chip size="small" label={trigger.enabled ? "enabled" : "paused"} color={trigger.enabled ? "success" : "default"} sx={{ mt: 0.5 }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {trigger.kind === "schedule"
                        ? `${trigger.schedule?.type || "schedule"}`
                        : `${trigger.event?.source}/${trigger.event?.event_type}`}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" variant="outlined" label={trigger.action.type} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {trigger.next_run_at ? new Date(trigger.next_run_at).toLocaleString() : "-"}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      <Button size="small" disabled={busy} onClick={() => void testTrigger(trigger.id)}>
                        Test
                      </Button>
                      <Button size="small" disabled={busy} onClick={() => void toggleEnabled(trigger)}>
                        {trigger.enabled ? "Pause" : "Resume"}
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DashboardCard>

      <DashboardCard title="Run history" subtitle="Lease-protected worker results, approvals, and ledger links">
        {(runsData?.runs || []).length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No runs yet.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Run</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Ledger</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(runsData?.runs || []).map((run) => (
                <TableRow key={run.id}>
                  <TableCell>
                    <Chip
                      size="small"
                      label={run.status}
                      color={
                        run.status === "done"
                          ? "success"
                          : run.status === "failed"
                            ? "error"
                            : run.status === "awaiting_approval"
                              ? "warning"
                              : "default"
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                      {run.id.slice(0, 16)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{new Date(run.created_at).toLocaleString()}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                      {run.ledger_entry_id ? run.ledger_entry_id.slice(0, 12) : "-"}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {run.status === "awaiting_approval" ? (
                      <Button size="small" disabled={busy} onClick={() => void approveRun(run.id)}>
                        Approve
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DashboardCard>
    </Box>
  );
}

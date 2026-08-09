"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import {
  cancelA2ATask,
  createA2ATask,
  fetchA2AAgents,
  fetchA2AStatus,
  fetchA2ATasks,
  registerA2AAgent,
} from "@/lib/a2a-api";

export default function A2APage() {
  const { data: status, mutate: mutateStatus } = useSWR("a2a-status", fetchA2AStatus);
  const { data: agents = [], isLoading: agentsLoading, mutate: mutateAgents } = useSWR(
    "a2a-agents",
    fetchA2AAgents,
  );
  const { data: tasks = [], isLoading: tasksLoading, mutate: mutateTasks } = useSWR(
    "a2a-tasks",
    fetchA2ATasks,
  );

  const [description, setDescription] = React.useState("");
  const [agentId, setAgentId] = React.useState("keprix-local");
  const [newAgentId, setNewAgentId] = React.useState("");
  const [newAgentName, setNewAgentName] = React.useState("");
  const [newAgentCaps, setNewAgentCaps] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = async () => {
    await Promise.all([mutateStatus(), mutateAgents(), mutateTasks()]);
  };

  const onCreateTask = async () => {
    if (!description.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await createA2ATask({ description: description.trim(), agent_id: agentId || undefined });
      setDescription("");
      setMessage("Task created");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setBusy(false);
    }
  };

  const onRegisterAgent = async () => {
    if (!newAgentId.trim() || !newAgentName.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await registerA2AAgent({
        id: newAgentId.trim(),
        name: newAgentName.trim(),
        capabilities: newAgentCaps
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setNewAgentId("");
      setNewAgentName("");
      setNewAgentCaps("");
      setMessage("Agent registered");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register agent");
    } finally {
      setBusy(false);
    }
  };

  const onCancel = async (taskId: string) => {
    setBusy(true);
    setError(null);
    try {
      await cancelA2ATask(taskId);
      setMessage("Task cancelled");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel task");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="A2A"
        description="Agent-to-Agent registry and task management."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Modules", href: "/settings/modules" },
          { label: "A2A" },
        ]}
      />

      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
        <Button component="a" href="/agent-runtime" size="small" variant="outlined">
          Agent runtime
        </Button>
        <Chip size="small" label={`${status?.agent_count ?? 0} agents`} />
        <Chip size="small" label={`${status?.task_count ?? 0} tasks`} />
        {Object.entries(status?.tasks_by_status ?? {}).map(([key, value]) => (
          <Chip key={key} size="small" variant="outlined" label={`${key}: ${value}`} />
        ))}
      </Stack>

      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          mb: 3,
        }}
      >
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Create task
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              fullWidth
              multiline
              minRows={2}
            />
            <TextField
              select
              label="Agent"
              value={agentId}
              onChange={(event) => setAgentId(event.target.value)}
              fullWidth
            >
              {agents.map((agent) => (
                <MenuItem key={agent.id} value={agent.id}>
                  {agent.name}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" disabled={busy || !description.trim()} onClick={() => void onCreateTask()}>
              Create task
            </Button>
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Register agent
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              label="Agent id"
              value={newAgentId}
              onChange={(event) => setNewAgentId(event.target.value)}
              fullWidth
            />
            <TextField
              label="Name"
              value={newAgentName}
              onChange={(event) => setNewAgentName(event.target.value)}
              fullWidth
            />
            <TextField
              label="Capabilities (comma-separated)"
              value={newAgentCaps}
              onChange={(event) => setNewAgentCaps(event.target.value)}
              fullWidth
            />
            <Button
              variant="outlined"
              disabled={busy || !newAgentId.trim() || !newAgentName.trim()}
              onClick={() => void onRegisterAgent()}
            >
              Register
            </Button>
          </Stack>
        </Paper>
      </Box>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Agents
      </Typography>
      {agentsLoading ? <SkeletonList rows={2} rowHeight={56} /> : null}
      <Stack spacing={1} sx={{ mb: 3 }}>
        {agents.map((agent) => (
          <Paper key={agent.id} variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
              <Typography variant="subtitle1">{agent.name}</Typography>
              <Chip size="small" label={agent.id} />
              {(agent.capabilities || []).map((cap) => (
                <Chip key={cap} size="small" variant="outlined" label={cap} />
              ))}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {agent.description || "No description"}
            </Typography>
          </Paper>
        ))}
      </Stack>

      <Typography variant="h6" sx={{ mb: 1 }}>
        Tasks
      </Typography>
      {tasksLoading ? <SkeletonList rows={3} rowHeight={48} /> : null}
      {!tasksLoading && tasks.length === 0 ? (
        <Alert severity="info">No A2A tasks yet. Create one above to start tracking handoffs.</Alert>
      ) : null}
      {tasks.length > 0 ? (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Description</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>
                    <Typography variant="body2">{task.description}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {task.id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={task.status} />
                  </TableCell>
                  <TableCell>{task.agent_id || "-"}</TableCell>
                  <TableCell align="right">
                    {["pending", "running", "streaming"].includes(task.status) ? (
                      <Button size="small" color="warning" disabled={busy} onClick={() => void onCancel(task.id)}>
                        Cancel
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ) : null}
    </Box>
  );
}

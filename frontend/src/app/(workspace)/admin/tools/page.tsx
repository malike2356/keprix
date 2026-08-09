"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { IconCheck, IconTrash, IconTools, IconX } from "@tabler/icons-react";
import { useCallback, useState } from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock, SkeletonTable } from "@/components/ui/loading";
import StatCard from "@/components/admin/StatCard";
import EmptyState from "@/components/ui/EmptyState";
import { ceApi } from "@/lib/ce-api";

type GeneratedTool = {
  id: string;
  tool_name: string;
  description: string;
  status: string;
  task_that_triggered: string;
  sandbox_result?: { passed?: boolean; duration_ms?: number };
};

type ToolsPayload = {
  tools: GeneratedTool[];
};

async function fetchPendingTools(): Promise<GeneratedTool[]> {
  const response = await ceApi("/api/agent/tools/generated/pending");
  if (!response.ok) {
    throw new Error("Failed to load pending tools");
  }
  const payload = (await response.json()) as ToolsPayload;
  return payload.tools || [];
}

async function fetchAllGeneratedTools(): Promise<GeneratedTool[]> {
  const response = await ceApi("/api/agent/tools/generated");
  if (!response.ok) {
    throw new Error("Failed to load generated tools");
  }
  const payload = (await response.json()) as ToolsPayload;
  return payload.tools || [];
}

function statusColor(status: string): "default" | "success" | "warning" | "error" {
  const normalized = status.toLowerCase();
  if (normalized.includes("approve") || normalized === "active" || normalized === "installed") return "success";
  if (normalized.includes("pending")) return "warning";
  if (normalized.includes("reject") || normalized.includes("fail")) return "error";
  return "default";
}

function sandboxLabel(tool: GeneratedTool): string {
  if (!tool.sandbox_result) return "Not run";
  const passed = tool.sandbox_result.passed ? "Passed" : "Failed";
  const duration = tool.sandbox_result.duration_ms ? ` (${tool.sandbox_result.duration_ms}ms)` : "";
  return `${passed}${duration}`;
}

export default function AdminToolsPage() {
  const [actionError, setActionError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  const {
    data: pending = [],
    isLoading: pendingLoading,
    mutate: mutatePending,
  } = useSWR("generated-tools-pending", fetchPendingTools);

  const {
    data: all = [],
    isLoading: allLoading,
    mutate: mutateAll,
    error: loadError,
  } = useSWR("generated-tools-all", fetchAllGeneratedTools);

  const refresh = useCallback(async () => {
    await Promise.all([mutatePending(), mutateAll()]);
  }, [mutatePending, mutateAll]);

  const approve = async (id: string) => {
    setActingId(id);
    setActionError(null);
    try {
      const response = await ceApi(`/api/agent/tools/generated/${id}/approve`, { method: "POST" });
      if (!response.ok) {
        throw new Error("Approve failed");
      }
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setActingId(null);
    }
  };

  const reject = async (id: string) => {
    setActingId(id);
    setActionError(null);
    try {
      const response = await ceApi(`/api/agent/tools/generated/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: "Rejected from admin UI" }),
      });
      if (!response.ok) {
        throw new Error("Reject failed");
      }
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setActingId(null);
    }
  };

  const removeTool = async (tool: GeneratedTool) => {
    const confirmed = window.confirm(
      `Delete generated tool "${tool.tool_name}"?\n\nThis removes the proposal from history and any installed files for that tool.`,
    );
    if (!confirmed) return;
    setActingId(tool.id);
    setActionError(null);
    try {
      const response = await ceApi(`/api/agent/tools/generated/${tool.id}`, { method: "DELETE" });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Delete failed");
      }
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setActingId(null);
    }
  };

  const approvedCount = all.filter((tool) => {
    const status = tool.status.toLowerCase();
    return status.includes("approve") || status === "installed" || status === "active";
  }).length;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
            Tool Manager
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 640 }}>
            Review tools created by the mutation engine. Built-in tools stay read-only; generated tools must pass
            sandbox checks before you approve them for use. Delete removes the proposal and any installed files.
          </Typography>
        </Box>
        <Button component="a" href="/dashboard/tools" variant="outlined" size="small">
          Open full tool library
        </Button>
      </Box>

      {loadError ? (
        <Alert severity="error">{loadError instanceof Error ? loadError.message : "Failed to load tools"}</Alert>
      ) : null}
      {actionError ? (
        <Alert severity="error" onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Pending approval"
            value={pending.length}
            loading={pendingLoading}
            icon={<IconTools size={22} stroke={1.75} />}
            color="warning"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Generated tools"
            value={all.length}
            loading={allLoading}
            icon={<IconTools size={22} stroke={1.75} />}
            color="secondary"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            title="Approved"
            value={approvedCount}
            loading={allLoading}
            icon={<IconCheck size={22} stroke={1.75} />}
            color="success"
          />
        </Grid>
      </Grid>

      <DashboardCard
        title="Pending approval"
        subtitle="Sandboxed tools waiting for your decision"
        action={
          pending.length ? (
            <Button component="a" href="/dashboard/mutation" size="small" variant="text">
              View mutation queue
            </Button>
          ) : null
        }
      >
        {pendingLoading ? (
          <Stack spacing={1.5}>
            <SkeletonBlock height={120} />
            <SkeletonBlock height={120} />
          </Stack>
        ) : pending.length === 0 ? (
          <EmptyState
            title="No tools waiting for approval"
            description="When the mutation engine proposes a new tool, it will appear here for review."
            icon={<IconTools size={40} stroke={1.5} />}
            actionLabel="Open mutation queue"
            onAction={() => {
              window.location.href = "/dashboard/mutation";
            }}
          />
        ) : (
          <Stack spacing={2}>
            {pending.map((tool) => (
              <Box
                key={tool.id}
                sx={{
                  p: 2,
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  bgcolor: "background.default",
                }}
              >
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between">
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ mb: 0.5 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {tool.tool_name}
                      </Typography>
                      <Chip size="small" label={tool.status} color="warning" variant="outlined" />
                      <Chip
                        size="small"
                        label={sandboxLabel(tool)}
                        color={tool.sandbox_result?.passed ? "success" : "default"}
                        variant="outlined"
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {tool.description || "No description provided."}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      Triggered by: {tool.task_that_triggered || "Unknown task"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
                      ID: {tool.id}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ flexShrink: 0 }}>
                    <Button
                      variant="contained"
                      color="success"
                      size="small"
                      startIcon={<IconCheck size={16} stroke={1.75} />}
                      disabled={actingId === tool.id}
                      onClick={() => void approve(tool.id)}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="outlined"
                      color="inherit"
                      size="small"
                      startIcon={<IconX size={16} stroke={1.75} />}
                      disabled={actingId === tool.id}
                      onClick={() => void reject(tool.id)}
                    >
                      Reject
                    </Button>
                    <Button
                      variant="outlined"
                      color="error"
                      size="small"
                      startIcon={<IconTrash size={16} stroke={1.75} />}
                      disabled={actingId === tool.id}
                      onClick={() => void removeTool(tool)}
                    >
                      Delete
                    </Button>
                  </Stack>
                </Stack>
              </Box>
            ))}
          </Stack>
        )}
      </DashboardCard>

      <DashboardCard title="All generated tools" subtitle="History of mutation-engine tool proposals">
        {allLoading ? (
          <SkeletonTable rows={6} columns={6} />
        ) : all.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No generated tools yet. Run the mutation engine or coding workspace to create one.
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Task</TableCell>
                <TableCell>Sandbox</TableCell>
                <TableCell>ID</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {all.map((tool) => (
                <TableRow key={tool.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {tool.tool_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                      {tool.description}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={tool.status} color={statusColor(tool.status)} variant="outlined" />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 220 }}>
                    <Typography variant="caption" color="text.secondary" noWrap title={tool.task_that_triggered}>
                      {tool.task_that_triggered || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{sandboxLabel(tool)}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                      {tool.id}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      color="error"
                      aria-label={`Delete ${tool.tool_name}`}
                      disabled={actingId === tool.id}
                      onClick={() => void removeTool(tool)}
                    >
                      <IconTrash size={16} stroke={1.75} />
                    </IconButton>
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

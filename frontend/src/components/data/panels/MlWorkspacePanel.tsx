"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
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
import EmptyState from "@/components/ui/EmptyState";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import {
  createMlExperiment,
  createMlRun,
  fetchMlExperiments,
  fetchMlModelRegistry,
  fetchMlRuns,
  type MlExperiment,
} from "@/lib/ml-api";

export default function MlWorkspacePanel() {
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [selected, setSelected] = React.useState<MlExperiment | null>(null);
  const [name, setName] = React.useState("");
  const [taskType, setTaskType] = React.useState("classification");

  const experiments = useSWR("ml-experiments", fetchMlExperiments);
  const runs = useSWR(selected ? ["ml-runs", selected.experiment_id] : null, () =>
    fetchMlRuns(selected!.experiment_id),
  );
  const registry = useSWR("ml-registry", fetchMlModelRegistry);

  const disabled =
    experiments.error &&
    String(experiments.error.message || "").toLowerCase().includes("not found");

  if (disabled) {
    return (
      <EmptyState
        title="ML workspace unavailable"
        description="The ML backend routes are not enabled in this runtime. No fake experiments are shown."
      />
    );
  }

  async function onCreateExperiment() {
    setBusy(true);
    setError(null);
    try {
      await createMlExperiment({ name: name.trim(), task_type: taskType.trim() || "task" });
      setName("");
      setMessage("Experiment created.");
      await experiments.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCreateRun() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await createMlRun({ experiment_id: selected.experiment_id, metrics: {} });
      setMessage("Run recorded.");
      await runs.mutate();
      await registry.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  const items = experiments.data?.items ?? [];

  return (
    <Box>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          New experiment
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <TextField
            size="small"
            label="Task type"
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
          />
          <Button
            variant="contained"
            disabled={busy || !name.trim()}
            onClick={() => void onCreateExperiment()}
          >
            Create
          </Button>
        </Stack>
      </Paper>

      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Experiments
      </Typography>
      {experiments.isLoading ? (
        <SkeletonTable rows={4} />
      ) : items.length === 0 ? (
        <EmptyState title="No experiments" description="Create an experiment to track runs and metrics." />
      ) : (
        <Table size="small" sx={{ mb: 2 }}>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Task</TableCell>
              <TableCell>Created</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((row) => (
              <TableRow
                key={row.experiment_id}
                hover
                selected={selected?.experiment_id === row.experiment_id}
                onClick={() => setSelected(row)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell>{row.name}</TableCell>
                <TableCell>{row.task_type || "-"}</TableCell>
                <TableCell>{row.created_at || "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {selected ? (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle1" sx={{ flex: 1 }}>
              Runs: {selected.name}
            </Typography>
            <Button size="small" disabled={busy} onClick={() => void onCreateRun()}>
              New run
            </Button>
          </Stack>
          {(runs.data?.items || []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No runs yet.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Run</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Metrics</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(runs.data?.items || []).map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell>{run.run_id}</TableCell>
                    <TableCell>{run.status || "-"}</TableCell>
                    <TableCell>
                      <StructuredDataView value={run.metrics || {}} emptyLabel="-" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      ) : null}

      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Model registry
      </Typography>
      {(registry.data?.items || []).length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No registry entries yet.
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Run</TableCell>
              <TableCell>Experiment</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Artifact</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(registry.data?.items || []).map((row) => (
              <TableRow key={row.run_id}>
                <TableCell>{row.run_id}</TableCell>
                <TableCell>{row.experiment_id}</TableCell>
                <TableCell>{row.status || "-"}</TableCell>
                <TableCell>{row.artifact_path || "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Box>
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import {
  cancelLocalJob,
  fetchLocalJobs,
  relatedObjectHref,
  retryLocalJob,
  type LocalJob,
} from "@/lib/jobs-api";

function statusColor(status: string): "default" | "success" | "warning" | "error" | "info" {
  switch (status) {
    case "completed":
      return "success";
    case "pending":
    case "claimed":
    case "running":
      return "info";
    case "failed":
    case "dead_letter":
      return "error";
    case "cancelled":
      return "warning";
    default:
      return "default";
  }
}

export default function JobsQueuePanel() {
  const [status, setStatus] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [confirm, setConfirm] = React.useState<{ job: LocalJob; action: "retry" | "cancel" } | null>(
    null,
  );

  const jobs = useSWR(["local-jobs", status], () => fetchLocalJobs(status || undefined), {
    refreshInterval: 15000,
  });
  const dead = useSWR("local-jobs-dead", () => fetchLocalJobs("dead_letter"));

  const rows = jobs.data?.items ?? [];
  const deadCount = dead.data?.items?.length ?? 0;

  async function runAction() {
    if (!confirm) return;
    setBusy(true);
    setError(null);
    try {
      if (confirm.action === "retry") {
        await retryLocalJob(confirm.job.job_id);
        setMessage(`Retry queued for ${confirm.job.job_id}.`);
      } else {
        await cancelLocalJob(confirm.job.job_id);
        setMessage(`Cancelled ${confirm.job.job_id}.`);
      }
      setConfirm(null);
      await jobs.mutate();
      await dead.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      {deadCount > 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {deadCount} dead-letter job{deadCount === 1 ? "" : "s"} need operator attention.
          <Button size="small" sx={{ ml: 1 }} onClick={() => setStatus("dead_letter")}>
            Show dead letters
          </Button>
        </Alert>
      ) : null}
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

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2 }} alignItems="center">
        <TextField
          select
          size="small"
          label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All</MenuItem>
          {["pending", "claimed", "running", "completed", "failed", "cancelled", "dead_letter"].map(
            (s) => (
              <MenuItem key={s} value={s}>
                {s}
              </MenuItem>
            ),
          )}
        </TextField>
        <Button size="small" onClick={() => void jobs.mutate()}>
          Refresh
        </Button>
        <Button component={NextLink} href="/admin/cron" size="small" variant="outlined">
          Cron jobs
        </Button>
        <Button component={NextLink} href="/crm/jobs" size="small" variant="outlined">
          CRM discovery jobs
        </Button>
      </Stack>

      {jobs.isLoading ? (
        <SkeletonTable rows={5} />
      ) : rows.length === 0 ? (
        <EmptyState title="No jobs" description="Background jobs from data import, research, and ML appear here." />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Workspace</TableCell>
              <TableCell>Attempts</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell>Error</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((job) => {
              const related = relatedObjectHref(job);
              const canCancel = ["pending", "claimed", "running"].includes(job.status);
              const canRetry = ["dead_letter", "failed"].includes(job.status);
              return (
                <TableRow key={job.job_id}>
                  <TableCell>
                    <Typography variant="body2">{job.job_type}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {job.job_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={job.status} color={statusColor(job.status)} />
                  </TableCell>
                  <TableCell>{job.workspace_id || "default"}</TableCell>
                  <TableCell>{job.retry_count ?? 0}</TableCell>
                  <TableCell>{job.updated_at || job.created_at || "-"}</TableCell>
                  <TableCell>
                    <Typography variant="caption" sx={{ maxWidth: 220, display: "block" }}>
                      {job.dead_letter_reason || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      {related ? (
                        <Button component={NextLink} href={related} size="small">
                          Open
                        </Button>
                      ) : null}
                      {canCancel ? (
                        <Button
                          size="small"
                          color="warning"
                          disabled={busy}
                          onClick={() => setConfirm({ job, action: "cancel" })}
                        >
                          Cancel
                        </Button>
                      ) : null}
                      {canRetry ? (
                        <Button
                          size="small"
                          color="error"
                          disabled={busy}
                          onClick={() => setConfirm({ job, action: "retry" })}
                        >
                          Retry
                        </Button>
                      ) : null}
                    </Stack>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      <Dialog open={Boolean(confirm)} onClose={() => setConfirm(null)}>
        <DialogTitle>
          {confirm?.action === "retry" ? "Retry dead-letter job?" : "Cancel job?"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: {confirm?.action} {confirm?.job.job_id} ({confirm?.job.job_type}).
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Back</Button>
          <Button
            color={confirm?.action === "retry" ? "error" : "warning"}
            variant="contained"
            disabled={busy}
            onClick={() => void runAction()}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

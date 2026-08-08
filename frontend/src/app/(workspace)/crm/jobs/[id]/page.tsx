"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  cancelCrmJob,
  fetchCrmJob,
  materializeCrmJob,
  retryCrmJob,
  runCrmJob,
} from "@/lib/crm-api";

export default function CrmJobDetailPage() {
  const params = useParams();
  const jobId = String(params?.id || "");
  const workspaceId = CRM_WORKSPACE;
  const detail = useSWR(jobId ? ["crm-job", workspaceId, jobId] : null, () =>
    fetchCrmJob(jobId, workspaceId),
  );
  const [busy, setBusy] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  const job = detail.data?.job;
  const kind = detail.data?.kind;

  const act = async (action: "cancel" | "run" | "materialize" | "retry") => {
    setBusy(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "cancel") await cancelCrmJob(jobId, workspaceId);
      if (action === "run") await runCrmJob(jobId, { force: true }, workspaceId);
      if (action === "materialize")
        await materializeCrmJob(jobId, { force: true }, workspaceId);
      if (action === "retry") await retryCrmJob(jobId, { force: true }, workspaceId);
      setMessage(`${action} completed`);
      await detail.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action}`);
    } finally {
      setBusy(null);
    }
  };

  if (!jobId) {
    return <Alert severity="error">Missing job id</Alert>;
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Button component={Link} href="/crm/jobs" size="small">
          Back to jobs
        </Button>
        <Button component={Link} href="/crm/discover" size="small" variant="outlined">
          Discover
        </Button>
      </Stack>

      {detail.error ? (
        <Alert severity="error">
          {detail.error instanceof Error ? detail.error.message : "Could not load job"}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      {detail.isLoading && !detail.data ? (
        <Typography color="text.secondary">Loading job...</Typography>
      ) : !job ? (
        <Typography color="text.secondary">Job not found.</Typography>
      ) : (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {kind === "discovery" ? "Discovery job" : "Job"} {jobId}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Adapter {String(job.adapter || "-")} · status {String(job.status || "-")} · pack{" "}
              {String(job.domain_pack || "generic")}
            </Typography>
            {detail.data?.adapter_health ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Adapter health: {String(detail.data.adapter_health.status)}
                {detail.data.adapter_health.message
                  ? `; ${detail.data.adapter_health.message}`
                  : ""}
              </Typography>
            ) : null}
            {job.cost_estimate != null ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Cost estimate: {String(job.cost_estimate)}
              </Typography>
            ) : null}
            {job.error ? (
              <Alert severity="warning" sx={{ mb: 1.5 }}>
                {String(job.error)}
              </Alert>
            ) : null}
            {job.list_id ? (
              <Typography variant="body2" sx={{ mb: 1.5 }}>
                Draft list:{" "}
                <Typography
                  component={Link}
                  href={`/crm/lists/${encodeURIComponent(String(job.list_id))}`}
                  color="primary"
                  sx={{ textDecoration: "underline" }}
                >
                  {String(job.list_id)}
                </Typography>
              </Typography>
            ) : null}

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                size="small"
                variant="outlined"
                disabled={!!busy}
                onClick={() => act("cancel")}
              >
                Cancel
              </Button>
              <Button
                size="small"
                variant="outlined"
                disabled={!!busy}
                onClick={() => act("run")}
              >
                Resume / run
              </Button>
              <Button
                size="small"
                variant="contained"
                disabled={!!busy}
                onClick={() => act("materialize")}
              >
                Soft Wall materialize
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="warning"
                disabled={!!busy}
                onClick={() => act("retry")}
              >
                Retry dead-letter
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}

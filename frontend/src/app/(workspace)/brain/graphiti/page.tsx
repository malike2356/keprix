"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
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
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type StatusPayload = {
  status: string;
  url?: string;
  error?: string;
  backend?: string;
  episodes?: number;
};
type GraphitiJob = {
  job_id: string;
  source_type: string;
  source_ref: string;
  status: string;
  nodes_added: number;
  edges_added: number;
  graphiti_episode_id?: string | null;
  error?: string | null;
};

async function fetchStatus(): Promise<StatusPayload> {
  const response = await ceApi("/api/brain/graphiti/status");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as StatusPayload;
}

async function fetchJobs(): Promise<GraphitiJob[]> {
  const response = await ceApi("/api/brain/graphiti/jobs");
  if (!response.ok) return [];
  const payload = (await response.json()) as { jobs: GraphitiJob[] };
  return payload.jobs;
}

function statusColor(status?: string): "success" | "warning" | "error" | "default" {
  if (status === "connected") return "success";
  if (status === "misconfigured" || status === "disabled") return "warning";
  if (status === "unreachable") return "error";
  return "default";
}

export default function GraphitiPage() {
  const { data: status, mutate: mutateStatus, error: statusError } = useSWR("graphiti-status", fetchStatus);
  const { data: jobs, mutate: mutateJobs } = useSWR("graphiti-jobs", fetchJobs);
  const [sourceType, setSourceType] = React.useState("manual");
  const [sourceRef, setSourceRef] = React.useState("manual-note");
  const [content, setContent] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [queryResult, setQueryResult] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const connected = status?.status === "connected";

  const ingest = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const response = await ceApi("/api/brain/graphiti/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_type: sourceType,
          source_ref: sourceRef,
          content: content || undefined,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setMessage(parseApiErrorMessage(payload, await response.text()));
        return;
      }
      const payload = (await response.json()) as { job: GraphitiJob };
      setMessage(
        payload.job.status === "failed"
          ? payload.job.error || "Ingest failed"
          : `Job ${payload.job.job_id} complete (${payload.job.nodes_added} nodes, ${payload.job.edges_added} edges)`,
      );
      await mutateJobs();
      await mutateStatus();
    } finally {
      setBusy(false);
    }
  };

  const runQuery = async () => {
    setBusy(true);
    setQueryResult(null);
    try {
      const response = await ceApi("/api/brain/graphiti/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const text = await response.text();
      try {
        setQueryResult(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setQueryResult(text);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Graphiti bridge"
        description="Ingest reports, sessions, and vault notes into graph memory. Uses a built-in local store when no external Graphiti MCP URL is set."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Brain" },
          { label: "Graphiti" },
        ]}
        actions={
          <Button onClick={() => void mutateStatus()} variant="outlined">
            Refresh status
          </Button>
        }
      />

      {statusError ? (
        <Alert severity="error">Could not load Graphiti status. Sign in and retry.</Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
        <Chip label={status?.status || "checking"} color={statusColor(status?.status)} />
        <Typography variant="body2" color="text.secondary">
          {status?.url || "checking…"}
          {status?.backend ? ` (${status.backend})` : ""}
          {typeof status?.episodes === "number" ? ` · ${status.episodes} episode(s)` : ""}
        </Typography>
        {status?.error ? (
          <Typography color="error" variant="body2">
            {status.error}
          </Typography>
        ) : null}
      </Paper>

      {!connected && status?.status ? (
        <Alert severity="warning">
          Graphiti is {status.status}. Set `GRAPHITI_MCP_URL` to an external MCP, or leave it empty to use the
          built-in local store (`builtin://graphiti`).
        </Alert>
      ) : null}

      {connected && status?.backend === "builtin" ? (
        <Alert severity="info">
          Built-in Graphiti store is active for this Keprix home. Point `GRAPHITI_MCP_URL` at a real Graphiti MCP when
          you want temporal graph retrieval from an external server.
        </Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="h6">Ingest</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "180px 1fr auto" } }}>
          <TextField select label="Source" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
            {["manual", "research", "session", "vault_file"].map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Source ref" value={sourceRef} onChange={(event) => setSourceRef(event.target.value)} />
          <Button variant="contained" disabled={!sourceRef || busy || !connected} onClick={() => void ingest()}>
            Ingest
          </Button>
        </Box>
        <TextField
          label="Manual content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          multiline
          minRows={4}
          placeholder="Paste a note or report excerpt to graph."
        />
        {message ? (
          <Typography color={message.toLowerCase().includes("fail") ? "error" : "text.secondary"}>{message}</Typography>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="h6">Query debugger</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr auto" } }}>
          <TextField label="Query" value={query} onChange={(event) => setQuery(event.target.value)} />
          <Button variant="outlined" disabled={!query || busy || !connected} onClick={() => void runQuery()}>
            Query
          </Button>
        </Box>
        {queryResult ? (
          <Typography component="pre" sx={{ whiteSpace: "pre-wrap", m: 0, fontFamily: "monospace", fontSize: 13 }}>
            {queryResult}
          </Typography>
        ) : null}
      </Paper>

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="h6">Recent jobs</Typography>
        </Box>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Job</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Nodes</TableCell>
              <TableCell>Edges</TableCell>
              <TableCell>Episode</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(jobs || []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <Typography variant="body2" color="text.secondary">
                    No ingest jobs yet.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              (jobs || []).map((job) => (
                <TableRow key={job.job_id}>
                  <TableCell>{job.job_id}</TableCell>
                  <TableCell>
                    {job.source_type}:{job.source_ref}
                  </TableCell>
                  <TableCell>{job.status}</TableCell>
                  <TableCell>{job.nodes_added}</TableCell>
                  <TableCell>{job.edges_added}</TableCell>
                  <TableCell>{job.graphiti_episode_id || job.error || "-"}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}

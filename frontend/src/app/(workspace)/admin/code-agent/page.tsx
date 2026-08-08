"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import {
  fetchCodeAgentSession,
  fetchCodeAgentSessions,
  fetchCodeAgentTrace,
  pauseCodeAgentSession,
  resumeCodeAgentSession,
  type CodingSession,
} from "@/lib/code-agent-api";

export default function CodeAgentSessionsPage() {
  const [selected, setSelected] = React.useState<CodingSession | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const sessions = useSWR("code-agent-sessions", () => fetchCodeAgentSessions());
  const detail = useSWR(selected ? ["code-agent-session", selected.id] : null, () =>
    fetchCodeAgentSession(selected!.id),
  );
  const trace = useSWR(selected ? ["code-agent-trace", selected.id] : null, () =>
    fetchCodeAgentTrace(selected!.id),
  );
  const rows = sessions.data?.sessions ?? [];

  return (
    <Box>
      <PageHeader
        title="Code-agent sessions"
        description="Operator view of /api/code-agent sessions (distinct from /admin/coding ladder)."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Code-agent" }]}
        actions={
          <Button component={NextLink} href="/admin/coding" size="small" variant="outlined">
            Coding ladder
          </Button>
        }
      />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {sessions.isLoading ? (
        <SkeletonTable rows={4} />
      ) : rows.length === 0 ? (
        <EmptyState title="No sessions" description="Start a code-agent session via API or agent tools." />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Objective</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id} hover selected={selected?.id === row.id} onClick={() => setSelected(row)} sx={{ cursor: "pointer" }}>
                <TableCell>{row.objective || row.id}</TableCell>
                <TableCell><Chip size="small" label={row.status || "-"} /></TableCell>
                <TableCell>{row.provider || "-"}</TableCell>
                <TableCell>{row.updated_at || row.created_at || "-"}</TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button size="small" disabled={busy} onClick={async () => {
                      setBusy(true); setError(null);
                      try { await pauseCodeAgentSession(row.id); await sessions.mutate(); }
                      catch (err) { setError(err instanceof Error ? err.message : "Pause failed"); }
                      finally { setBusy(false); }
                    }}>Pause</Button>
                    <Button size="small" disabled={busy} onClick={async () => {
                      setBusy(true); setError(null);
                      try { await resumeCodeAgentSession(row.id); await sessions.mutate(); }
                      catch (err) { setError(err instanceof Error ? err.message : "Resume failed"); }
                      finally { setBusy(false); }
                    }}>Resume</Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {selected ? (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
          <Typography variant="subtitle1">Session {selected.id}</Typography>
          <StructuredDataView value={detail.data?.session || selected} />
          <Typography variant="subtitle2" sx={{ mt: 2 }}>Trace</Typography>
          <StructuredDataView value={trace.data?.events || []} />
        </Paper>
      ) : null}
    </Box>
  );
}

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
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";

type IsolationFinding = {
  check: string;
  severity: string;
  description: string;
  fix_available?: boolean;
  count?: number;
  fix_description?: string | null;
};

type IsolationReport = {
  run_at: string;
  passed: boolean;
  summary?: {
    total_findings?: number;
    by_severity?: Record<string, number>;
    checks_run?: number;
    passed?: boolean;
  };
  findings: IsolationFinding[];
  checks_run?: string[];
  duration_seconds?: number;
};

async function fetchAudit() {
  const response = await ceApi("/api/admin/isolation-audit");
  if (!response.ok) throw new Error("Could not load isolation audit");
  return (await response.json()) as {
    latest: IsolationReport | null;
    history: IsolationReport[];
    count: number;
  };
}

function severityColor(severity: string): "error" | "warning" | "info" | "default" {
  if (severity === "critical" || severity === "high") return "error";
  if (severity === "medium") return "warning";
  if (severity === "low") return "info";
  return "default";
}

export default function IsolationAuditPage() {
  const { data, error, isLoading, mutate } = useSWR("isolation-audit", fetchAudit, {
    refreshInterval: 30_000,
  });
  const [busy, setBusy] = React.useState(false);
  const [runError, setRunError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  const runAudit = async (fix: boolean) => {
    setBusy(true);
    setRunError(null);
    setMessage(null);
    try {
      const response = await ceApi("/api/admin/isolation-audit/run", {
        method: "POST",
        body: JSON.stringify({ fix }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as { report: IsolationReport };
      setMessage(
        payload.report.passed
          ? `Audit passed (${payload.report.summary?.total_findings ?? 0} findings).`
          : `Audit finished with findings (${payload.report.summary?.total_findings ?? 0}).`,
      );
      await mutate();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Audit run failed");
    } finally {
      setBusy(false);
    }
  };

  const latest = data?.latest ?? null;

  return (
    <Box>
      <PageHeader
        title="Isolation audit"
        description="Verify product and workspace isolation boundaries. Run checks and review findings."
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" disabled={busy} onClick={() => runAudit(false)}>
              Run now
            </Button>
            <Button variant="contained" disabled={busy} onClick={() => runAudit(true)}>
              Run with fix
            </Button>
          </Stack>
        }
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Could not load isolation audit"}
        </Alert>
      ) : null}
      {runError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {runError}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      {isLoading ? <SkeletonList rows={4} rowHeight={56} /> : null}

      {!isLoading && !latest ? (
        <Paper variant="outlined" sx={{ p: 3, mb: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            No isolation audits yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
            Run an audit to check orphaned rows, grant hygiene, unprotected routes, and related isolation invariants.
          </Typography>
          <Button variant="contained" disabled={busy} onClick={() => runAudit(false)}>
            Run first audit
          </Button>
        </Paper>
      ) : null}

      {latest ? (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }} sx={{ mb: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>
              Latest run
            </Typography>
            <Chip
              size="small"
              label={latest.passed ? "PASS" : "FAIL"}
              color={latest.passed ? "success" : "error"}
            />
            <Typography variant="body2" color="text.secondary">
              {new Date(latest.run_at).toLocaleString()}
              {latest.duration_seconds != null ? ` · ${latest.duration_seconds.toFixed(2)}s` : ""}
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {latest.summary?.total_findings ?? latest.findings?.length ?? 0} findings
            {latest.checks_run?.length ? ` across ${latest.checks_run.length} checks` : ""}
          </Typography>

          {(latest.findings?.length ?? 0) === 0 ? (
            <Typography variant="body2">No findings in this run.</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Severity</TableCell>
                  <TableCell>Check</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {latest.findings.map((finding, index) => (
                  <TableRow key={`${finding.check}-${index}`}>
                    <TableCell>
                      <Chip size="small" label={finding.severity} color={severityColor(finding.severity)} />
                    </TableCell>
                    <TableCell>{finding.check}</TableCell>
                    <TableCell>{finding.description}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      ) : null}

      {(data?.history?.length ?? 0) > 1 ? (
        <Paper variant="outlined" sx={{ overflow: "auto" }}>
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="subtitle2">History</Typography>
          </Box>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>When</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Findings</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.history.slice(1).map((row) => (
                <TableRow key={row.run_at}>
                  <TableCell>{new Date(row.run_at).toLocaleString()}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.passed ? "PASS" : "FAIL"} color={row.passed ? "success" : "error"} />
                  </TableCell>
                  <TableCell>{row.summary?.total_findings ?? row.findings?.length ?? 0}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ) : null}
    </Box>
  );
}

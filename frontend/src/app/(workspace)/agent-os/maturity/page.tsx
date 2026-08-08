"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import LevelUpPanel from "./LevelUpPanel";
import { AGENT_OS_HUB_HOME } from "@/components/agent-os/AgentOsSubnav";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonBlock } from "@/components/ui/loading";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type Score = { dimension: string; score: number; max_score: number; strengths: string[]; gaps: string[] };
type Audit = {
  audit_id: string;
  workspace_id?: string | null;
  total_score: number;
  scores: Score[];
  top_gaps: Array<{ rank: number; title: string; dimension: string; fix_hint: string }>;
  scanned_at: string;
};

export default function MaturityPage() {
  const [workspaceId, setWorkspaceId] = React.useState("personal-os");
  const [workspacePath, setWorkspacePath] = React.useState("");
  const [audit, setAudit] = React.useState<Audit | null>(null);
  const [history, setHistory] = React.useState<Audit[]>([]);
  const [exportPayload, setExportPayload] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const [historyLoading, setHistoryLoading] = React.useState(true);

  const parse = async <T,>(response: Response, fallback: string): Promise<T> => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(parseApiErrorMessage(payload, fallback));
    return payload as T;
  };

  const refresh = React.useCallback(async () => {
    const payload = await parse<{ audits: Audit[] }>(await ceApi("/api/agent-os/maturity"), "Could not load audits");
    setHistory(payload.audits);
  }, []);

  React.useEffect(() => {
    setHistoryLoading(true);
    refresh()
      .catch(() => undefined)
      .finally(() => setHistoryLoading(false));
  }, [refresh]);

  const run = async () => {
    setBusy(true);
    setError(null);
    setExportPayload(null);
    try {
      const payload = await parse<{ audit: Audit }>(
        await ceApi("/api/agent-os/maturity/run", {
          method: "POST",
          body: JSON.stringify({ workspace_id: workspaceId.trim() || "personal-os", workspace_path: workspacePath.trim() || undefined }),
        }),
        "Maturity audit failed",
      );
      setAudit(payload.audit);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Maturity audit failed");
    } finally {
      setBusy(false);
    }
  };

  const exportLevelUp = async () => {
    if (!audit) return;
    const payload = await parse<Record<string, unknown>>(
      await ceApi(`/api/agent-os/maturity/${encodeURIComponent(audit.audit_id)}/export-to-level-up`, { method: "POST" }),
      "Export failed",
    );
    setExportPayload(payload);
  };

  const active = audit || history[0] || null;

  return (
    <Box>
      <PageHeader
        title="OS maturity"
        description="Four C's audit for your personal OS workspace. Optional after activation."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: AGENT_OS_HUB_HOME },
          { label: "Maturity" },
        ]}
      />
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ md: "flex-end" }}>
            <TextField label="Workspace id" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} size="small" />
            <TextField label="Workspace path" value={workspacePath} onChange={(event) => setWorkspacePath(event.target.value)} size="small" fullWidth />
            <Button variant="contained" disabled={busy} onClick={() => void run()}>
              {busy ? "Running..." : "Run audit"}
            </Button>
          </Stack>
        </CardContent>
      </Card>
      {error ? (
        <Box sx={{ mb: 2 }}>
          <ErrorState title="Maturity audit failed" message={error} />
        </Box>
      ) : null}
      {historyLoading && !active ? <SkeletonBlock height={160} /> : null}
      {!historyLoading && !active && !error ? (
        <EmptyState
          title="No maturity audits yet"
          description="Run an audit to score Capture, Chat, Curate, and Create for this workspace."
          actionLabel="Run audit"
          onAction={() => void run()}
        />
      ) : null}
      {active ? (
        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Box sx={{ width: 120 }}>
                  <Typography variant="h3">{Math.round(active.total_score)}</Typography>
                  <Typography variant="body2" color="text.secondary">/ 100</Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <LinearProgress variant="determinate" value={active.total_score} sx={{ mb: 1 }} />
                  <Typography variant="body2" color="text.secondary">{active.audit_id}</Typography>
                </Box>
                <Button variant="outlined" onClick={() => void exportLevelUp()}>Export to level-up</Button>
              </Stack>
            </CardContent>
          </Card>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { md: "1fr 1fr" } }}>
            {active.scores.map((score) => (
              <Card key={score.dimension} variant="outlined">
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                    <Typography variant="subtitle1">{score.dimension}</Typography>
                    <Chip label={`${score.score}/${score.max_score}`} />
                  </Stack>
                  <LinearProgress variant="determinate" value={(score.score / score.max_score) * 100} sx={{ mb: 1 }} />
                  <Typography variant="caption" color="text.secondary">Gaps</Typography>
                  <Box component="ul" sx={{ mt: 0.5, pl: 2 }}>
                    {score.gaps.map((gap) => <li key={gap}><Typography variant="body2">{gap}</Typography></li>)}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>Top gaps</Typography>
              {active.top_gaps.map((gap) => (
                <Typography key={`${gap.rank}-${gap.title}`} variant="body2" sx={{ mb: 0.75 }}>
                  {gap.rank}. {gap.title} - {gap.fix_hint}
                </Typography>
              ))}
            </CardContent>
          </Card>
          <LevelUpPanel auditId={active.audit_id} workspacePath={workspacePath.trim() || undefined} />
          {exportPayload ? (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Level-up export
                </Typography>
                <StructuredDataView value={exportPayload} />
              </CardContent>
            </Card>
          ) : null}
        </Stack>
      ) : null}
    </Box>
  );
}

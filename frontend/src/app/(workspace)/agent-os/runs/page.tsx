"use client";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";
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
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type LedgerEntry = {
  entry_id: string;
  source_type: string;
  source_id: string;
  run_id: string;
  workspace_id: string;
  status: string;
  eval_score: number | null;
  tokens: number;
  duration_ms: number;
  created_at: string;
};

const sourceTypes = ["", "playbook", "skill", "agent_app", "cron"];

export default function AgentOsRunsPage() {
  const router = useRouter();
  const search = useSearchParams();
  const [sourceType, setSourceType] = React.useState(search.get("source_type") || "");
  const [sourceId, setSourceId] = React.useState(search.get("source_id") || "");
  const [runId, setRunId] = React.useState(search.get("run_id") || "");
  const [entries, setEntries] = React.useState<LedgerEntry[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    const params = new URLSearchParams();
    if (sourceType) params.set("source_type", sourceType);
    if (sourceId) params.set("source_id", sourceId);
    const response = await ceApi(`/api/agent-os/ledger?${params.toString()}`);
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    const payload = (await response.json()) as { entries: LedgerEntry[] };
    const filtered = runId ? payload.entries.filter((entry) => entry.run_id.includes(runId)) : payload.entries;
    setEntries(filtered);
    setMessage(null);
  }, [runId, sourceId, sourceType]);

  React.useEffect(() => {
    void load();
  }, [load]);

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Run ledger"
        description="Unified execution log for playbooks, skills, Agent Apps, and scheduled automations."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Runs" },
        ]}
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "180px 1fr 1fr auto" }, alignItems: "center" }}>
        <TextField select label="Source type" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
          {sourceTypes.map((type) => (
            <MenuItem key={type || "all"} value={type}>{type || "All"}</MenuItem>
          ))}
        </TextField>
        <TextField label="Source ID" value={sourceId} onChange={(event) => setSourceId(event.target.value)} />
        <TextField label="Run ID" value={runId} onChange={(event) => setRunId(event.target.value)} />
        <Button variant="outlined" onClick={() => void load()}>
          Refresh
        </Button>
      </Box>
      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Source</TableCell>
              <TableCell>Run</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Eval</TableCell>
              <TableCell align="right">Tokens</TableCell>
              <TableCell align="right">Duration</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Profile</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.entry_id} hover>
                <TableCell>
                  <Typography variant="body2">{entry.source_id}</Typography>
                  <Typography variant="caption" color="text.secondary">{entry.source_type}</Typography>
                </TableCell>
                <TableCell>{entry.run_id}</TableCell>
                <TableCell><Chip size="small" label={entry.status} /></TableCell>
                <TableCell align="right">{entry.eval_score == null ? "-" : entry.eval_score.toFixed(2)}</TableCell>
                <TableCell align="right">{entry.tokens.toLocaleString()}</TableCell>
                <TableCell align="right">{entry.duration_ms} ms</TableCell>
                <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    endIcon={<OpenInNewIcon fontSize="small" />}
                    onClick={() => router.push(`/agent-os/loop-profiles?source=${encodeURIComponent(`${entry.source_type}:${entry.source_id}`)}`)}
                  >
                    Open
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      {entries.length === 0 && <Typography color="text.secondary">No ledger entries match these filters.</Typography>}
      {message && <Typography color="error">{message}</Typography>}
    </Box>
  );
}

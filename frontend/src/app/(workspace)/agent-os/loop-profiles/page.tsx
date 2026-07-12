"use client";

import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
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
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Proposal = {
  proposal_id: string;
  category: string;
  title: string;
  detail: string;
  status: string;
  draft_path?: string;
  metadata?: Record<string, unknown>;
};

export default function AgentOsLoopProfilesPage() {
  const search = useSearchParams();
  const [source, setSource] = React.useState(search.get("source") || "playbook:");
  const [lastN, setLastN] = React.useState(5);
  const [proposals, setProposals] = React.useState<Proposal[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);

  const loadProposals = React.useCallback(async () => {
    if (!source.includes(":") || source.endsWith(":")) return;
    const response = await ceApi(`/api/agent-os/loop-profiles/${encodeURIComponent(source)}/proposals`);
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    const payload = (await response.json()) as { proposals: Proposal[] };
    setProposals(payload.proposals);
    setMessage(null);
  }, [source]);

  React.useEffect(() => {
    void loadProposals();
  }, [loadProposals]);

  const captureBaseline = async () => {
    const response = await ceApi(`/api/agent-os/loop-profiles/${encodeURIComponent(source)}/baseline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ last_n: lastN }),
    });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setMessage("Baseline captured");
    await loadProposals();
  };

  const applyProposal = async (proposalId: string) => {
    const response = await ceApi(`/api/agent-os/loop-profiles/proposals/${proposalId}/apply`, { method: "POST" });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    const payload = (await response.json()) as { draft_path: string };
    setMessage(`Draft created at ${payload.draft_path}`);
    await loadProposals();
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Loop profiles"
        description="Compare automation runs to baselines and create draft improvements for review."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Loop profiles" },
        ]}
      />
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 140px auto auto" }, alignItems: "center" }}>
        <TextField label="Source" value={source} onChange={(event) => setSource(event.target.value)} />
        <TextField label="Baseline runs" type="number" value={lastN} onChange={(event) => setLastN(Number(event.target.value || 1))} />
        <Button variant="outlined" onClick={() => void captureBaseline()} disabled={!source.includes(":") || source.endsWith(":")}>
          Capture baseline
        </Button>
        <Button variant="contained" onClick={() => void loadProposals()} disabled={!source.includes(":") || source.endsWith(":")}>
          Analyze
        </Button>
      </Box>
      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Proposal</TableCell>
              <TableCell>Signal</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {proposals.map((proposal) => (
              <TableRow key={proposal.proposal_id} hover>
                <TableCell>
                  <Typography variant="body2">{proposal.title}</Typography>
                  <Typography variant="caption" color="text.secondary">{proposal.detail}</Typography>
                </TableCell>
                <TableCell><Chip size="small" label={proposal.category} /></TableCell>
                <TableCell>{proposal.status}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    startIcon={<AutoFixHighIcon fontSize="small" />}
                    onClick={() => void applyProposal(proposal.proposal_id)}
                  >
                    Draft
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      {proposals.length === 0 && (
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip size="small" label="No drift" />
          <Typography color="text.secondary">No loop profile proposals are open for this source.</Typography>
        </Stack>
      )}
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}

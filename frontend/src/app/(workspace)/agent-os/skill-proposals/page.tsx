"use client";

import CheckIcon from "@mui/icons-material/Check";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type SkillProposal = {
  proposal_id: string;
  source: string;
  slug: string;
  name: string;
  description: string;
  status: string;
  occurrence_count: number;
  confidence: number;
  skill_path?: string | null;
};

async function api(path: string, init?: RequestInit) {
  const response = await ceApi(path, init);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function SkillProposalsPage() {
  const [proposals, setProposals] = React.useState<SkillProposal[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(async () => {
    setBusy(true);
    try {
      const payload = (await api("/api/agent-os/skill-proposals")) as { proposals: SkillProposal[] };
      setProposals(payload.proposals);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (path: string, success: string) => {
    setBusy(true);
    try {
      await api(path, { method: "POST" });
      setMessage(success);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Skill proposals"
        description="Review repeated-work candidates and package approved skills."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Skill proposals" },
        ]}
      />
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button disabled={busy} startIcon={<RefreshIcon />} onClick={() => void load()}>
          Refresh
        </Button>
        <Button disabled={busy} startIcon={<RefreshIcon />} onClick={() => void runAction("/api/agent-os/skill-proposals/import", "Imported audit proposals.")}>
          Import audit queue
        </Button>
        <Button disabled={busy} startIcon={<SearchIcon />} onClick={() => void runAction("/api/agent-os/skill-proposals/scan-sessions", "Scanned sessions for repeated work.")}>
          Scan sessions
        </Button>
      </Box>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Proposal</TableCell>
            <TableCell>Source</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Evidence</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {proposals.map((proposal) => (
            <TableRow key={proposal.proposal_id}>
              <TableCell>
                <Typography variant="body2">{proposal.name}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {proposal.slug}
                </Typography>
              </TableCell>
              <TableCell>{proposal.source}</TableCell>
              <TableCell>
                <Chip size="small" label={proposal.status} />
              </TableCell>
              <TableCell>
                {proposal.occurrence_count} run(s), {Math.round(proposal.confidence * 100)}%
              </TableCell>
              <TableCell align="right">
                <Button
                  size="small"
                  disabled={busy || proposal.status === "approved"}
                  startIcon={<CheckIcon />}
                  onClick={() => void runAction(`/api/agent-os/skill-proposals/${proposal.proposal_id}/approve`, "Skill packaged.")}
                >
                  Approve
                </Button>
                <Button
                  size="small"
                  disabled={busy || proposal.status === "rejected"}
                  color="error"
                  startIcon={<CloseIcon />}
                  onClick={() => void runAction(`/api/agent-os/skill-proposals/${proposal.proposal_id}/reject`, "Proposal rejected.")}
                >
                  Reject
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}

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
import Paper from "@mui/material/Paper";
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
import AgentOsSubnav from "@/components/agent-os/AgentOsSubnav";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import {
  applyImprovementProposal,
  approveImprovementProposal,
  deferImprovementProposal,
  fetchImprovementMetrics,
  fetchImprovementProposals,
  rejectImprovementProposal,
  type ImprovementProposal,
} from "@/lib/improvement-api";

export default function ImprovementsPage() {
  const [status, setStatus] = React.useState("");
  const [selected, setSelected] = React.useState<ImprovementProposal | null>(null);
  const [confirm, setConfirm] = React.useState<"apply" | "reject" | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const proposals = useSWR(["improvement-proposals", status], () =>
    fetchImprovementProposals(status || undefined),
  );
  const metrics = useSWR("improvement-metrics", () => fetchImprovementMetrics());

  async function runSoftWall() {
    if (!selected || !confirm) return;
    setBusy(true);
    setError(null);
    try {
      if (confirm === "apply") {
        await approveImprovementProposal(selected.proposal_id);
        await applyImprovementProposal(selected.proposal_id);
        setMessage(`Applied ${selected.proposal_id}`);
      } else {
        await rejectImprovementProposal(selected.proposal_id);
        setMessage(`Rejected ${selected.proposal_id}`);
      }
      setConfirm(null);
      await proposals.mutate();
      await metrics.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const rows = proposals.data?.proposals ?? [];

  return (
    <Box>
      <AgentOsSubnav />
      <PageHeader
        title="Improvement proposals"
        description="Review auto-improvement proposals from /api/improvement. Soft Wall still wins over auto_apply settings."
        breadcrumbs={[
          { label: "Agent OS", href: "/agent-os/glass" },
          { label: "Improvements" },
        ]}
        actions={
          <Button component={NextLink} href="/settings/agent/self-improvement" variant="outlined" size="small">
            Self-improvement settings
          </Button>
        }
      />

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
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Metrics
        </Typography>
        <StructuredDataView value={metrics.data || {}} emptyLabel="No metrics" />
      </Paper>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All</MenuItem>
          {["pending_approval", "approved", "rejected", "applied", "deferred"].map((s) => (
            <MenuItem key={s} value={s}>
              {s}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      {proposals.isLoading ? (
        <SkeletonTable rows={5} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No proposals"
          description="Enable detection in self-improvement settings, then wait for run analyzer proposals."
        />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={row.proposal_id}
                hover
                selected={selected?.proposal_id === row.proposal_id}
                onClick={() => setSelected(row)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell>{row.title || row.proposal_id}</TableCell>
                <TableCell>{row.category || "-"}</TableCell>
                <TableCell>
                  <Chip size="small" label={row.status || "unknown"} />
                </TableCell>
                <TableCell>{row.created_at || "-"}</TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      size="small"
                      disabled={busy}
                      onClick={() => {
                        setSelected(row);
                        setConfirm("apply");
                      }}
                    >
                      Soft Wall apply
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      disabled={busy}
                      onClick={() => {
                        setSelected(row);
                        setConfirm("reject");
                      }}
                    >
                      Reject
                    </Button>
                    <Button
                      size="small"
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await deferImprovementProposal(row.proposal_id);
                          await proposals.mutate();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Defer failed");
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      Defer
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {selected ? (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
          <Typography variant="subtitle1">{selected.title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {selected.proposal_id} · run {selected.run_id} · agent {selected.agent_id}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {selected.detail || "No detail"}
          </Typography>
          <Box sx={{ mt: 1 }}>
            <StructuredDataView value={selected.metadata || {}} emptyLabel="No metadata" />
          </Box>
        </Paper>
      ) : null}

      <Dialog open={Boolean(confirm)} onClose={() => setConfirm(null)}>
        <DialogTitle>
          {confirm === "apply" ? "Soft Wall apply proposal?" : "Reject proposal?"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirm === "apply"
              ? "Approve then mark applied. Soft Wall still wins even when auto_apply is enabled."
              : "Reject leaves runtime unchanged."}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(null)}>Cancel</Button>
          <Button
            color={confirm === "reject" ? "error" : "primary"}
            variant="contained"
            disabled={busy}
            onClick={() => void runSoftWall()}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

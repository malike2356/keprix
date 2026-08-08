"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
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
import { fetchCrmDeliverability, upsertSenderReadiness } from "@/lib/crm-api";

const WORKSPACE = "default";

export default function OutreachDeliverabilityPage() {
  const { data, error, isLoading, mutate } = useSWR(
    ["crm-deliverability", WORKSPACE],
    () => fetchCrmDeliverability(WORKSPACE),
  );
  const [domain, setDomain] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [spf, setSpf] = React.useState(false);
  const [dkim, setDkim] = React.useState(false);
  const [dmarc, setDmarc] = React.useState(false);
  const [verified, setVerified] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  const save = async () => {
    if (!domain.trim()) {
      setErr("Domain is required");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await upsertSenderReadiness(
        {
          domain: domain.trim(),
          verified,
          spf_ok: spf,
          dkim_ok: dkim,
          dmarc_ok: dmarc,
          notes: notes.trim() || undefined,
        },
        WORKSPACE,
      );
      setMsg("Sender readiness saved");
      setDomain("");
      await mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const rates = data?.rates;
  const checklist = data?.checklist;

  return (
    <Stack spacing={2}>
      {(error || err) && (
        <Alert severity="error" onClose={() => setErr(null)}>
          {error instanceof Error ? error.message : err}
        </Alert>
      )}
      {msg && (
        <Alert severity="success" onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      )}

      <Typography variant="body2" color="text.secondary">
        Sender readiness and bounce/complaint rates before cold Soft Wall send. Empty rates are
        honest zeros, not demo traffic.
      </Typography>

      {data?.soft_wall_block_cold_send ? (
        <Alert severity="warning">
          Soft Wall cold send blocked: {data.soft_wall_block_reason || "policy check failed"}.{" "}
          <Button component={NextLink} href="/outreach/settings" size="small">
            Open safety settings
          </Button>
        </Alert>
      ) : (
        <Alert severity="success">Deliverability checklist clear for cold send (subject to Soft Wall approvals).</Alert>
      )}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        {[
          ["Bounce %", rates?.bounce_rate_pct],
          ["Complaint %", rates?.complaint_rate_pct],
          ["Unsubscribe %", rates?.unsubscribe_rate_pct],
          ["Sent", rates?.sent_count],
        ].map(([label, value]) => (
          <Paper key={String(label)} variant="outlined" sx={{ p: 2, flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
            <Typography variant="h5">{isLoading ? "..." : String(value ?? 0)}</Typography>
          </Paper>
        ))}
      </Stack>

      {checklist ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Readiness checklist
          </Typography>
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {Object.entries(checklist).map(([key, ok]) => (
              <Chip
                key={key}
                size="small"
                label={key.replace(/_/g, " ")}
                color={ok ? "success" : "default"}
                variant={ok ? "filled" : "outlined"}
              />
            ))}
          </Stack>
          {data?.thresholds ? (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Policy thresholds: bounce {data.thresholds.bounce_rate_pct}%, complaint{" "}
              {data.thresholds.complaint_rate_pct}%, unsubscribe {data.thresholds.unsubscribe_rate_pct}%
            </Typography>
          ) : null}
        </Paper>
      ) : null}

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Domain</TableCell>
              <TableCell>Verified</TableCell>
              <TableCell>SPF</TableCell>
              <TableCell>DKIM</TableCell>
              <TableCell>DMARC</TableCell>
              <TableCell>Notes</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.sender_readiness ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>
                  <EmptyState
                    title="No sender domains yet"
                    description="Add a sending domain and mark SPF/DKIM/DMARC status honestly (unknown stays unchecked)."
                  />
                </TableCell>
              </TableRow>
            ) : (
              (data?.sender_readiness ?? []).map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.domain)}</TableCell>
                  <TableCell>{row.verified ? "yes" : "no"}</TableCell>
                  <TableCell>{row.spf_ok ? "ok" : "unknown"}</TableCell>
                  <TableCell>{row.dkim_ok ? "ok" : "unknown"}</TableCell>
                  <TableCell>{row.dmarc_ok ? "ok" : "unknown"}</TableCell>
                  <TableCell>{String(row.notes || "")}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Add / update sender domain
        </Typography>
        <Stack spacing={1}>
          <TextField size="small" label="Domain" value={domain} onChange={(e) => setDomain(e.target.value)} />
          <TextField size="small" label="Notes / warm-up" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Stack direction="row" flexWrap="wrap">
            <FormControlLabel control={<Switch checked={verified} onChange={(_, v) => setVerified(v)} />} label="Verified" />
            <FormControlLabel control={<Switch checked={spf} onChange={(_, v) => setSpf(v)} />} label="SPF ok" />
            <FormControlLabel control={<Switch checked={dkim} onChange={(_, v) => setDkim(v)} />} label="DKIM ok" />
            <FormControlLabel control={<Switch checked={dmarc} onChange={(_, v) => setDmarc(v)} />} label="DMARC ok" />
          </Stack>
          <Box>
            <Button variant="contained" disabled={busy} onClick={() => void save()}>
              Save readiness
            </Button>
            <Button component={NextLink} href="/outreach/settings" sx={{ ml: 1 }}>
              Kill switches
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Stack>
  );
}

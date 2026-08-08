"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import StructuredDataView from "@/components/ui/StructuredDataView";
import {
  bulkCrmSuppressions,
  createCrmSuppression,
  deleteCrmSuppression,
  fetchCrmSuppressions,
} from "@/lib/crm-api";

const WORKSPACE = "default";

export default function OutreachSuppressionsPage() {
  const { data, error, mutate, isLoading } = useSWR(["crm-suppressions", WORKSPACE], () =>
    fetchCrmSuppressions(WORKSPACE),
  );
  const [q, setQ] = React.useState("");
  const [channel, setChannel] = React.useState("email");
  const [address, setAddress] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [bulkCsv, setBulkCsv] = React.useState("");
  const [previewCount, setPreviewCount] = React.useState<number | null>(null);
  const [previewSample, setPreviewSample] = React.useState<unknown[] | null>(null);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [err, setErr] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const items = (data?.items ?? []).filter((row) => {
    if (!q.trim()) return true;
    const hay = `${row.address} ${row.channel} ${row.reason} ${row.source}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  const addOne = async () => {
    setBusy(true);
    setErr(null);
    try {
      await createCrmSuppression(
        { address: address.trim(), channel, reason: reason.trim() || "operator", source: "operator" },
        WORKSPACE,
      );
      setMsg("Suppression added");
      setAddress("");
      await mutate();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Add failed");
    } finally {
      setBusy(false);
    }
  };

  const parseBulk = () =>
    bulkCsv
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [addr, ch, why] = line.split(",").map((p) => p.trim());
        return { address: addr, channel: ch || "email", reason: why || "bulk_import", source: "operator_bulk" };
      });

  const runBulk = async (doPreview: boolean) => {
    setBusy(true);
    setErr(null);
    try {
      const rows = parseBulk();
      const result = await bulkCrmSuppressions(rows, { preview: doPreview }, WORKSPACE);
      if (doPreview) {
        setPreviewCount(result.count);
        setPreviewSample(Array.isArray(result.sample) ? result.sample : []);
      } else if (result.blocked) {
        setMsg("Soft Wall approval required for bulk import. See Approvals.");
      } else {
        setMsg(`Imported ${result.count} suppressions`);
        setBulkCsv("");
        setPreviewCount(null);
        setPreviewSample(null);
        await mutate();
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Bulk failed");
    } finally {
      setBusy(false);
    }
  };

  const undo = async (id: string) => {
    setBusy(true);
    setErr(null);
    try {
      const result = await deleteCrmSuppression(id, {}, WORKSPACE);
      if (result.blocked) setMsg("Soft Wall approval required to undo suppression.");
      else {
        setMsg("Suppression undone");
        await mutate();
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Undo failed");
    } finally {
      setBusy(false);
    }
  };

  const exportCsv = () => {
    const lines = ["channel,address,reason,source", ...items.map((r) =>
      [r.channel, r.address, r.reason || "", r.source || ""].join(","),
    )];
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "suppressions.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack spacing={2}>
      {error || err ? (
        <Alert severity="error" onClose={() => setErr(null)}>
          {error instanceof Error ? error.message : err}
        </Alert>
      ) : null}
      {msg ? (
        <Alert severity="success" onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      ) : null}
      {previewCount != null ? (
        <Alert severity="info" onClose={() => { setPreviewCount(null); setPreviewSample(null); }}>
          <Typography variant="body2" sx={{ mb: previewSample?.length ? 1 : 0 }}>
            Preview {previewCount} rows
          </Typography>
          {previewSample?.length ? <StructuredDataView value={previewSample} /> : null}
        </Alert>
      ) : null}

      <Typography variant="body2" color="text.secondary">
        Suppressions block enroll and send. Bounce/unsubscribe auto-entries appear with source. Undo is Soft Wall gated.
      </Typography>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" label="Search" value={q} onChange={(e) => setQ(e.target.value)} sx={{ flex: 1 }} />
        <Button variant="outlined" onClick={exportCsv} disabled={!items.length}>
          Export CSV (DSAR)
        </Button>
      </Stack>

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Channel</TableCell>
              <TableCell>Address</TableCell>
              <TableCell>Reason</TableCell>
              <TableCell>Source</TableCell>
              <TableCell align="right"> </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <EmptyState title="No suppressions" description="Workspace has no suppression entries yet." />
                </TableCell>
              </TableRow>
            ) : (
              items.map((row) => (
                <TableRow key={String(row.id)}>
                  <TableCell>{String(row.channel)}</TableCell>
                  <TableCell sx={{ fontFamily: "monospace" }}>{String(row.address)}</TableCell>
                  <TableCell>{String(row.reason || "")}</TableCell>
                  <TableCell>{String(row.source || "")}</TableCell>
                  <TableCell align="right">
                    <Button size="small" color="warning" disabled={busy} onClick={() => void undo(String(row.id))}>
                      Undo
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Add suppression
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="ch">Channel</InputLabel>
            <Select labelId="ch" label="Channel" value={channel} onChange={(e) => setChannel(String(e.target.value))}>
              {["email", "phone", "telegram"].map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField size="small" label="Address" value={address} onChange={(e) => setAddress(e.target.value)} sx={{ flex: 1 }} />
          <TextField size="small" label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} sx={{ flex: 1 }} />
          <Button variant="contained" disabled={busy || !address.trim()} onClick={() => void addOne()}>
            Add
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Bulk CSV (address[,channel][,reason] per line)
        </Typography>
        <TextField
          size="small"
          multiline
          minRows={4}
          fullWidth
          value={bulkCsv}
          onChange={(e) => setBulkCsv(e.target.value)}
          placeholder={"alice@example.com,email,opt_out\n+447700900123,phone,complaint"}
        />
        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
          <Button variant="outlined" disabled={busy || !bulkCsv.trim()} onClick={() => void runBulk(true)}>
            Soft Wall preview
          </Button>
          <Button variant="contained" disabled={busy || !bulkCsv.trim()} onClick={() => void runBulk(false)}>
            Import
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}

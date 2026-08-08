"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Paper from "@mui/material/Paper";
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
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { SkeletonTable } from "@/components/ui/loading";
import { fetchToolAdapters, runToolAdapter } from "@/lib/platform-admin-api";

export default function ToolAdaptersPage() {
  const adapters = useSWR("tool-adapters", () => fetchToolAdapters());
  const [selected, setSelected] = React.useState<string | null>(null);
  const [action, setAction] = React.useState("ping");
  const [result, setResult] = React.useState<unknown>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [confirm, setConfirm] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const rows = adapters.data?.adapters ?? [];

  async function run(approved: boolean) {
    if (!selected) return;
    setBusy(true); setError(null);
    try {
      setResult(await runToolAdapter(selected, { action, params: {}, dry_run: !approved, approved }));
      setConfirm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <PageHeader title="Tool adapters" description="Catalog and dry-run backend tool adapters." breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Tool adapters" }]} />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {adapters.isLoading ? <SkeletonTable rows={5} /> : rows.length === 0 ? (
        <EmptyState title="No adapters" description="Adapter registry is empty." />
      ) : (
        <Table size="small">
          <TableHead><TableRow><TableCell>Name</TableCell><TableCell>Category</TableCell><TableCell>Risk</TableCell><TableCell>Configured</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.map((row) => {
              const name = String(row.name || "");
              return (
                <TableRow key={name} hover selected={selected === name} onClick={() => setSelected(name)} sx={{ cursor: "pointer" }}>
                  <TableCell>{name}</TableCell>
                  <TableCell>{String(row.category || "-")}</TableCell>
                  <TableCell>{String(row.risk_level || "-")}</TableCell>
                  <TableCell>{String(row.configured)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
      {selected ? (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
          <Typography variant="subtitle1">{selected}</Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <TextField size="small" label="Action" value={action} onChange={(e) => setAction(e.target.value)} />
            <Button disabled={busy} onClick={() => void run(false)}>Dry run</Button>
            <Button color="warning" disabled={busy} onClick={() => setConfirm(true)}>Soft Wall run</Button>
          </Stack>
          {result ? <Box sx={{ mt: 1 }}><StructuredDataView value={result} /></Box> : null}
        </Paper>
      ) : null}
      <Dialog open={confirm} onClose={() => setConfirm(false)}>
        <DialogTitle>Approved adapter run?</DialogTitle>
        <DialogContent><DialogContentText>Soft Wall confirm: run {selected} with approved=true (not dry-run).</DialogContentText></DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirm(false)}>Cancel</Button>
          <Button color="warning" variant="contained" disabled={busy} onClick={() => void run(true)}>Confirm</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

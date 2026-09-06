"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
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
import PageContainer from "@/components/shared/PageContainer";
import { useRequireAdmin } from "@/lib/ce-auth";
import { bulkGrantAdminCredits, fetchAdminAivas } from "@/lib/admin-aivas-api";

export default function AdminAivasPage() {
  useRequireAdmin();
  const { data, error, mutate } = useSWR("admin-aivas", fetchAdminAivas);
  const [batchId, setBatchId] = React.useState("");
  const [reason, setReason] = React.useState("");
  const [grants, setGrants] = React.useState("user-id,100");
  const [message, setMessage] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);

  const submit = async () => {
    const items = grants.split("\n").map((line) => {
      const [userId, amount] = line.split(",").map((item) => item.trim());
      return { user_id: userId, amount: Number(amount) };
    }).filter((item) => item.user_id && Number.isInteger(item.amount) && item.amount > 0);
    if (!batchId.trim() || !reason.trim() || !items.length) {
      setMessage("Enter a batch ID, reason, and at least one user,amount row.");
      return;
    }
    setSaving(true);
    try {
      await bulkGrantAdminCredits({ batch_id: batchId.trim(), reason: reason.trim(), grants: items });
      setMessage("Credit batch processed");
      await mutate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Credit batch failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageContainer title="Aiva operations" description="Platform-wide worker visibility and audited credit grants." padded={false}>
      <Stack spacing={3}>
        {message ? <Alert severity="info" onClose={() => setMessage(null)}>{message}</Alert> : null}
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h6">Bulk credit grant</Typography>
            <TextField label="Batch ID" value={batchId} onChange={(event) => setBatchId(event.target.value)} />
            <TextField label="Reason" value={reason} onChange={(event) => setReason(event.target.value)} />
            <TextField label="User ID, amount per line" multiline minRows={3} value={grants} onChange={(event) => setGrants(event.target.value)} />
            <Button variant="contained" onClick={() => void submit()} disabled={saving}>{saving ? "Processing..." : "Process grant"}</Button>
          </Stack>
        </Paper>
        {error ? <Alert severity="error">{error.message}</Alert> : null}
        <Paper variant="outlined" sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead><TableRow><TableCell>Workspace</TableCell><TableCell>Worker</TableCell><TableCell>Status</TableCell><TableCell>Channels</TableCell><TableCell>Tokens</TableCell><TableCell>Cost</TableCell><TableCell>Last activity</TableCell></TableRow></TableHead>
            <TableBody>{(data || []).map((row) => <TableRow key={`${row.workspace_id}:${row.worker_id}`}><TableCell>{row.workspace_id}</TableCell><TableCell>{row.worker_id}</TableCell><TableCell>{row.status}</TableCell><TableCell>{row.channels.join(", ") || "-"}</TableCell><TableCell>{row.tokens}</TableCell><TableCell>${row.cost_usd.toFixed(4)}</TableCell><TableCell>{row.last_activity || "-"}</TableCell></TableRow>)}</TableBody>
          </Table>
        </Paper>
      </Stack>
    </PageContainer>
  );
}

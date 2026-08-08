"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { createCrmSuppression, deleteCrmSuppression, fetchCrmSuppressions } from "@/lib/crm-api";

export default function CrmSuppressionsPage() {
  const [address, setAddress] = React.useState("");
  const [reason, setReason] = React.useState("unsubscribe");
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const list = useSWR(["crm-suppressions", CRM_WORKSPACE], () => fetchCrmSuppressions(CRM_WORKSPACE));

  const add = async () => {
    setError(null);
    try {
      await createCrmSuppression({ address, channel: "email", reason, source: "ui" }, CRM_WORKSPACE);
      setAddress("");
      setMessage("Suppression added");
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  };

  const undo = async (id: string) => {
    setError(null);
    try {
      const result = await deleteCrmSuppression(id, {}, CRM_WORKSPACE);
      if (result.blocked) {
        setMessage(`Soft Wall required: ${result.approval?.id || ""}`);
        return;
      }
      setMessage("Suppression undone");
      await list.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Undo failed");
    }
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 720 }}>
      <Typography variant="body2" color="text.secondary">
        Suppression always wins over consent. Discovery is not contact permission.
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField size="small" fullWidth label="Email / phone / telegram" value={address} onChange={(e) => setAddress(e.target.value)} />
        <TextField size="small" label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button variant="contained" onClick={() => void add()}>
          Add
        </Button>
      </Stack>
      {(list.data?.items || []).map((row) => (
        <Stack key={String(row.id)} direction="row" spacing={1} alignItems="center">
          <Typography variant="body2" sx={{ flex: 1 }}>
            {String(row.channel)} · {String(row.address)} · {String(row.reason || "")}
          </Typography>
          <Button size="small" onClick={() => void undo(String(row.id))}>
            Undo
          </Button>
        </Stack>
      ))}
      {!list.isLoading && (list.data?.items || []).length === 0 ? (
        <Typography color="text.secondary">No suppressions.</Typography>
      ) : null}
    </Stack>
  );
}

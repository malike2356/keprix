"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { fetchDsarRequests, requestDsarDelete, requestDsarExport } from "@/lib/parity-api";

export default function DsarAdminPage() {
  const { data, mutate, error } = useSWR("dsar-requests", fetchDsarRequests, { shouldRetryOnError: false });
  const [subject, setSubject] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [last, setLast] = React.useState<Record<string, unknown> | null>(null);

  const run = async (fn: () => Promise<Record<string, unknown>>) => {
    setBusy(true);
    setActionError(null);
    try {
      setLast(await fn());
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader title="DSAR" description="Operator export and erasure requests backed by the privacy pipeline." />
      {error ? <Alert severity="warning" sx={{ mb: 2 }}>Admin access required.</Alert> : null}
      {actionError ? <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 2 }}>
        <TextField
          size="small"
          label="Subject user id"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
        />
        <Button
          variant="contained"
          disabled={busy || !subject.trim()}
          onClick={() => void run(async () => (await requestDsarExport(subject.trim())).request)}
        >
          Export now
        </Button>
        <Button
          variant="outlined"
          disabled={busy || !subject.trim()}
          onClick={() => void run(async () => requestDsarDelete(subject.trim(), true))}
        >
          Delete dry-run
        </Button>
      </Stack>
      <Typography variant="h6">Requests</Typography>
      <Stack spacing={1} sx={{ mt: 1 }}>
        {(data?.requests || []).map((row) => (
          <Box key={String(row.id)} sx={{ borderBottom: 1, borderColor: "divider", py: 1 }}>
            <Typography fontWeight={600}>
              {String(row.request_type || row.kind || "request")} · {String(row.status)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {String(row.user_id || row.subject_user_id)} · {String(row.id)}
              {row.export_path ? ` · ${String(row.export_path)}` : ""}
            </Typography>
          </Box>
        ))}
        {!data?.requests?.length ? <Typography color="text.secondary">No DSAR requests yet.</Typography> : null}
      </Stack>
      {last ? (
        <Box sx={{ mt: 2 }}>
          <StructuredDataView value={last} />
        </Box>
      ) : null}
    </Box>
  );
}

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
import { createLead, fetchLeads } from "@/lib/parity-api";

export default function LeadsPage() {
  const { data, mutate, error } = useSWR("leads", fetchLeads);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const onCreate = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await createLead({ name: name.trim(), email: email.trim() || undefined });
      setName("");
      setEmail("");
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader title="Leads" subtitle="Thin lead list linked to contacts and viCal bookings." />
      {error ? <Alert severity="error" sx={{ mb: 2 }}>Failed to load leads</Alert> : null}
      {actionError ? <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert> : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ mb: 3 }}>
        <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField size="small" label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Button variant="contained" disabled={busy || !name.trim()} onClick={() => void onCreate()}>
          Create lead
        </Button>
      </Stack>
      <Stack spacing={1}>
        {(data?.leads || []).map((lead) => (
          <Box key={String(lead.id)} sx={{ borderBottom: 1, borderColor: "divider", py: 1 }}>
            <Typography fontWeight={600}>{String(lead.name)}</Typography>
            <Typography variant="body2" color="text.secondary">
              {String(lead.email || "(no email)")}
              {lead.vical_booking_id ? ` · booking ${String(lead.vical_booking_id)}` : ""}
            </Typography>
          </Box>
        ))}
        {!data?.leads?.length ? <Typography color="text.secondary">No leads yet.</Typography> : null}
      </Stack>
    </Box>
  );
}

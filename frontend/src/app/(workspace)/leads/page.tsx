"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList } from "@/components/ui/loading";
import { createLead, fetchLeads } from "@/lib/parity-api";

export default function ProductLeadsPage() {
  const leads = useSWR("product-leads", fetchLeads);
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      await createLead({ name: name.trim(), email: email.trim() || undefined });
      setName("");
      setEmail("");
      setMessage("Product signup lead created.");
      await leads.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  const rows = leads.data?.leads ?? [];

  return (
    <Box>
      <PageHeader
        title="Product signups"
        description="Product signup leads from /api/leads (not Soft Wall outreach, not CRM). Use Outreach leads for sales engagement and CRM leads for funnel records."
        breadcrumbs={[{ label: "Workspace", href: "/home" }, { label: "Product signups" }]}
        actions={
          <Stack direction="row" spacing={1}>
            <Button component="a" href="/outreach/leads" size="small" variant="outlined">
              Outreach leads
            </Button>
            <Button component="a" href="/crm/leads" size="small" variant="outlined">
              CRM leads
            </Button>
          </Stack>
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
      <Alert severity="info" sx={{ mb: 2 }}>
        Three lead systems stay separate: Product signups (`/leads`), Outreach / Soft Wall leads
        (`/outreach/leads`), and CRM leads (`/crm/leads`).
      </Alert>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
        <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <TextField size="small" label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Button variant="contained" disabled={busy || !name.trim()} onClick={() => void onCreate()}>
          Add signup
        </Button>
      </Stack>
      {leads.isLoading ? (
        <SkeletonList rows={4} rowHeight={48} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No product signup leads"
          description="Create a signup lead here, or open Outreach / CRM if you meant sales engagement."
        />
      ) : (
        <List dense>
          {rows.map((row) => (
            <ListItemButton key={String(row.id || row.email || row.name)}>
              <ListItemText
                primary={String(row.name || "Unnamed")}
                secondary={String(row.email || row.id || "")}
              />
            </ListItemButton>
          ))}
        </List>
      )}
    </Box>
  );
}

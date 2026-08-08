"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import { pipelineLabel } from "@/components/outreach/types";
import {
  createOutreachLead,
  createdCount,
  fetchOutreachLeads,
  importOutreachLeads,
} from "@/lib/outreach-api";

const WORKSPACE = "default";

export default function OutreachLeadsPage() {
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [bulk, setBulk] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const leads = useSWR(["outreach-leads", WORKSPACE], () => fetchOutreachLeads(WORKSPACE, { limit: 200 }));

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!name.trim()) throw new Error("Name is required");
      await createOutreachLead(
        { name: name.trim(), email: email.trim() || undefined, company: company.trim() || undefined, phone: phone.trim() || undefined, source: "manual" },
        WORKSPACE,
      );
      setName("");
      setEmail("");
      setCompany("");
      setPhone("");
      setMessage("Lead saved");
      await leads.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create lead");
    } finally {
      setBusy(false);
    }
  };

  const onImport = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!bulk.trim()) throw new Error("Paste lead lines first");
      const result = await importOutreachLeads({ lines: bulk, csv_text: bulk }, WORKSPACE);
      setBulk("");
      setMessage(`Imported ${createdCount(result.created)} lead(s)`);
      await leads.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Alert severity="info">
        Outreach / Soft Wall leads for sales engagement. Product signups live at{" "}
        <Link href="/leads">/leads</Link>. CRM funnel leads live at{" "}
        <Link href="/crm/leads">/crm/leads</Link>.
      </Alert>
      <Typography variant="h5">Outreach leads</Typography>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Add lead
              </Typography>
              <Stack spacing={1.5}>
                <TextField size="small" label="Name" value={name} onChange={(e) => setName(e.target.value)} />
                <TextField size="small" label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
                <TextField size="small" label="Company" value={company} onChange={(e) => setCompany(e.target.value)} />
                <TextField size="small" label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
                <Button size="small" variant="contained" disabled={busy} onClick={() => void onCreate()}>
                  Save lead
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Bulk import
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                One lead per line: name | email | company | phone (CSV also accepted)
              </Typography>
              <TextField
                fullWidth
                multiline
                minRows={5}
                value={bulk}
                onChange={(e) => setBulk(e.target.value)}
                placeholder={"Ada Lovelace | ada@example.com | Analytical Engines | +44..."}
              />
              <Button size="small" variant="contained" sx={{ mt: 1.5 }} disabled={busy} onClick={() => void onImport()}>
                Import
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {leads.isLoading && !leads.data ? (
        <Typography color="text.secondary">Loading leads...</Typography>
      ) : (leads.data?.leads ?? []).length === 0 ? (
        <Typography color="text.secondary">No leads yet.</Typography>
      ) : (
        <Stack spacing={1}>
          {(leads.data?.leads ?? []).map((lead) => (
            <Card key={lead.id} variant="outlined">
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="center">
                  <Stack spacing={0.25} sx={{ minWidth: 0 }}>
                    <Typography
                      component={Link}
                      href={`/outreach/leads/${lead.id}`}
                      variant="body2"
                      fontWeight={600}
                      sx={{ color: "primary.main", textDecoration: "none" }}
                    >
                      {lead.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" noWrap>
                      {pipelineLabel(lead.status)}
                      {lead.email ? ` · ${lead.email}` : ""}
                      {lead.company ? ` · ${lead.company}` : ""}
                      {lead.source ? ` · ${lead.source}` : ""}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    {(lead.tags ?? []).slice(0, 3).map((tag) => (
                      <Chip key={tag} size="small" label={tag} variant="outlined" />
                    ))}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      )}
    </Stack>
  );
}

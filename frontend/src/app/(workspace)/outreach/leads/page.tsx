"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
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

const SOURCE_LABELS: Record<string, string> = {
  companies_house: "Companies House",
  csv_import: "Spreadsheet import",
  google_maps: "Google Maps",
  listing_page: "Listing page",
  manual: "Manual",
  scrape: "Internet research",
  web: "Internet research",
  youtube_comment: "YouTube",
};

function sourceLabel(source?: string | null): string {
  if (!source) return "Unknown";
  return SOURCE_LABELS[source] ?? source.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function safeSourceUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export default function OutreachLeadsPage() {
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [source, setSource] = React.useState("manual");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [bulk, setBulk] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [sourceFilter, setSourceFilter] = React.useState("all");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const leads = useSWR(["outreach-leads", WORKSPACE], () => fetchOutreachLeads(WORKSPACE, { limit: 200 }));
  const rows = React.useMemo(() => leads.data?.leads ?? [], [leads.data?.leads]);
  const sources = React.useMemo(
    () => Array.from(new Set(rows.map((lead) => lead.source).filter((value): value is string => Boolean(value)))).sort(),
    [rows],
  );
  const filteredRows = React.useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((lead) => {
      if (sourceFilter !== "all" && lead.source !== sourceFilter) return false;
      if (!needle) return true;
      return [lead.name, lead.company, lead.email, lead.phone, lead.source, lead.source_url, lead.sourceUrl]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [query, rows, sourceFilter]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!name.trim()) throw new Error("Name is required");
      await createOutreachLead(
        {
          name: name.trim(),
          email: email.trim() || undefined,
          company: company.trim() || undefined,
          phone: phone.trim() || undefined,
          source,
          source_url: sourceUrl.trim() || undefined,
        },
        WORKSPACE,
      );
      setName("");
      setEmail("");
      setCompany("");
      setPhone("");
      setSource("manual");
      setSourceUrl("");
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
                <TextField select size="small" label="Lead source" value={source} onChange={(e) => setSource(e.target.value)}>
                  <MenuItem value="manual">Manual</MenuItem>
                  <MenuItem value="web">Internet research</MenuItem>
                  <MenuItem value="companies_house">Companies House</MenuItem>
                  <MenuItem value="listing_page">Listing page</MenuItem>
                  <MenuItem value="google_maps">Google Maps</MenuItem>
                  <MenuItem value="csv_import">Spreadsheet import</MenuItem>
                </TextField>
                <TextField
                  size="small"
                  label="Source page URL"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://..."
                />
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

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
        <TextField
          fullWidth
          size="small"
          label="Search leads"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <TextField
          select
          size="small"
          label="Source"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          sx={{ minWidth: 210 }}
        >
          <MenuItem value="all">All sources</MenuItem>
          {sources.map((value) => <MenuItem key={value} value={value}>{sourceLabel(value)}</MenuItem>)}
        </TextField>
        <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
          {filteredRows.length} lead{filteredRows.length === 1 ? "" : "s"}
        </Typography>
      </Stack>

      {leads.isLoading && !leads.data ? (
        <Typography color="text.secondary">Loading leads...</Typography>
      ) : rows.length === 0 ? (
        <Typography color="text.secondary">No leads yet.</Typography>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Outreach lead tracker">
            <TableHead>
              <TableRow>
                <TableCell>Lead</TableCell>
                <TableCell>Company</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Source page</TableCell>
                <TableCell>Stage</TableCell>
                <TableCell>Date added</TableCell>
                <TableCell>Tags</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRows.map((lead) => {
                const originUrl = safeSourceUrl(lead.source_url ?? lead.sourceUrl);
                const createdAt = lead.created_at ?? lead.createdAt;
                return (
                  <TableRow key={lead.id} hover>
                    <TableCell>
                      <Link href={`/outreach/leads/${lead.id}`} style={{ fontWeight: 600 }}>{lead.name}</Link>
                    </TableCell>
                    <TableCell>{lead.company || "-"}</TableCell>
                    <TableCell>{lead.email || "-"}</TableCell>
                    <TableCell>{lead.phone || "-"}</TableCell>
                    <TableCell><Chip size="small" label={sourceLabel(lead.source)} variant="outlined" /></TableCell>
                    <TableCell>
                      {originUrl ? <a href={originUrl} target="_blank" rel="noreferrer">Open source</a> : "-"}
                    </TableCell>
                    <TableCell>{pipelineLabel(lead.status)}</TableCell>
                    <TableCell>{createdAt ? new Date(createdAt).toLocaleDateString() : "-"}</TableCell>
                    <TableCell>{(lead.tags ?? []).slice(0, 3).join(", ") || "-"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}

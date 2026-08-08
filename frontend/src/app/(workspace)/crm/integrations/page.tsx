"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { approveCrmApproval } from "@/lib/crm-api";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

async function fetchIntegrations() {
  const res = await ceApi(`/api/crm/integrations?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`);
  if (!res.ok) throw new Error(parseApiErrorMessage(await res.json().catch(() => ({})), "Integrations failed"));
  return res.json();
}

export default function CrmIntegrationsPage() {
  const [csv, setCsv] = React.useState("email,first_name,last_name,company\n");
  const [provider, setProvider] = React.useState("csv");
  const [stage, setStage] = React.useState("");
  const [preview, setPreview] = React.useState<Record<string, unknown> | null>(null);
  const [exportOut, setExportOut] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const data = useSWR(["crm-integrations"], fetchIntegrations);

  const runPreview = async () => {
    setError(null);
    setMessage(null);
    try {
      const res = await ceApi(`/api/crm/integrations/preview?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, payload: csv }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Preview failed"));
      setPreview(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    }
  };

  const applyImport = async () => {
    setError(null);
    setMessage(null);
    try {
      let res = await ceApi(`/api/crm/integrations/import?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, payload: csv }),
      });
      let payload = await res.json();
      if (payload?.blocked && payload?.approval?.id) {
        await approveCrmApproval(payload.approval.id, CRM_WORKSPACE);
        res = await ceApi(`/api/crm/integrations/import?workspace_id=${encodeURIComponent(CRM_WORKSPACE)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider, payload: csv, approval_id: payload.approval.id }),
        });
        payload = await res.json();
      }
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Import failed"));
      if (payload.blocked) {
        setError("Soft Wall approval required. Approve on /crm then retry Soft Wall apply.");
        return;
      }
      setMessage(`Import applied: created ${payload.created}, updated ${payload.updated}, skipped ${payload.skipped}`);
      setPreview(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  };

  const runExport = async () => {
    setError(null);
    try {
      const qs = new URLSearchParams({
        workspace_id: CRM_WORKSPACE,
        provider,
      });
      if (stage.trim()) qs.set("stage", stage.trim());
      const res = await ceApi(`/api/crm/integrations/export?${qs.toString()}`);
      const payload = await res.json();
      if (!res.ok) throw new Error(parseApiErrorMessage(payload, "Export failed"));
      setExportOut(payload);
      if (payload.status === "not_configured") {
        setMessage(`${provider} is not_configured; export refused without credentials.`);
      } else {
        setMessage(`Export ready (${payload.count ?? 0} rows, mode ${payload.mode || provider})`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 900 }}>
      <Typography variant="h5">CRM integrations</Typography>
      <Typography variant="body2" color="text.secondary">
        HubSpot / Salesforce / Pipedrive / GHL adapters. Missing API keys show not_configured. CSV always works.
        Configure tokens under{" "}
        <Typography component={Link} href="/crm/settings#connections" color="primary" sx={{ textDecoration: "underline" }}>
          /crm/settings Connections
        </Typography>
        . Soft Wall gates apply. Field mappings:{" "}
        <Typography component={Link} href="/docs" color="primary" sx={{ textDecoration: "underline" }}>
          docs/features/crm-integrations.md
        </Typography>
        .
      </Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Adapter status</Typography>
          {(data.data?.adapters || []).map((a: { provider: string; status: string; message?: string }) => (
            <Typography key={a.provider} variant="body2">
              {a.provider}: {a.status}
              {a.message ? ` (${a.message})` : ""}
            </Typography>
          ))}
          {data.data?.field_mappings ? (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Mapping keys available for: {Object.keys(data.data.field_mappings).join(", ")}
            </Typography>
          ) : null}
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">CSV / provider import (Soft Wall before apply)</Typography>
          <FormControl size="small" sx={{ mt: 1, minWidth: 180 }}>
            <InputLabel id="provider-label">Provider</InputLabel>
            <Select
              labelId="provider-label"
              label="Provider"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {["csv", "ghl", "hubspot", "salesforce", "pipedrive"].map((p) => (
                <MenuItem key={p} value={p}>
                  {p}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            multiline
            minRows={6}
            fullWidth
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            sx={{ mt: 1 }}
          />
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button variant="outlined" onClick={() => void runPreview()}>
              Preview
            </Button>
            <Button variant="contained" onClick={() => void applyImport()}>
              Soft Wall apply
            </Button>
          </Stack>
          {preview ? (
            <Stack sx={{ mt: 1 }}>
              <StructuredDataView value={preview.counts || preview} />
            </Stack>
          ) : null}
        </CardContent>
      </Card>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1">Export</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mt: 1 }}>
            <TextField
              size="small"
              label="Stage filter (optional)"
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              placeholder="qualified"
            />
            <Button variant="outlined" onClick={() => void runExport()}>
              Export {provider}
            </Button>
          </Stack>
          {exportOut?.csv ? (
            <TextField
              multiline
              minRows={4}
              fullWidth
              value={String(exportOut.csv)}
              sx={{ mt: 1 }}
              InputProps={{ readOnly: true }}
            />
          ) : exportOut ? (
            <Stack sx={{ mt: 1 }}>
              <StructuredDataView value={exportOut} />
            </Stack>
          ) : null}
        </CardContent>
      </Card>
    </Stack>
  );
}

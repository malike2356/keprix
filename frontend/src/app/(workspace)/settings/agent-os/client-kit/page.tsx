"use client";

import DownloadIcon from "@mui/icons-material/Download";
import UploadIcon from "@mui/icons-material/Upload";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Paper from "@mui/material/Paper";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";
import { fetchSimplifiedMode, saveSimplifiedMode, type SimplifiedModeConfig } from "@/lib/simplifiedMode";

type Preview = {
  pins: number;
  cron_jobs: number;
  playbooks: string[];
  agent_apps: string[];
  secrets: string[];
};

async function fetchPreview(): Promise<Preview> {
  const response = await ceApi("/api/agent-os/client-kit/preview");
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as Preview;
}

export default function ClientKitSettingsPage() {
  const { data: preview, mutate: mutatePreview } = useSWR("client-kit-preview", fetchPreview);
  const { data: simplified, mutate: mutateSimplified } = useSWR("simplified-mode", fetchSimplifiedMode);
  const [name, setName] = React.useState("client");
  const [includeWorkspace, setIncludeWorkspace] = React.useState(true);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const exportKit = async () => {
    setBusy(true);
    try {
      const response = await ceApi("/api/agent-os/client-kit/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, include_workspace_template: includeWorkspace }),
      });
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob();
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `client-kit-${name}.zip`;
      link.click();
      URL.revokeObjectURL(href);
      setMessage("Client kit exported");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const importKit = async (file: File | null) => {
    if (!file) return;
    const form = new FormData();
    form.set("file", file);
    const response = await ceApi("/api/agent-os/client-kit/import", { method: "POST", body: form });
    if (!response.ok) {
      setMessage(await response.text());
      return;
    }
    setMessage("Client kit imported");
    await mutatePreview();
  };

  const updateSimplified = async (patch: Partial<SimplifiedModeConfig>) => {
    if (!simplified) return;
    const saved = await saveSimplifiedMode({ ...simplified, ...patch });
    await mutateSimplified(saved, false);
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Client kit"
        description="Export handoff bundles and configure simplified mode for recipients."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Settings", href: "/settings" },
          { label: "Client kit" },
        ]}
      />
      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="h6">Export</Typography>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr auto" }, alignItems: "center" }}>
          <TextField label="Kit name" value={name} onChange={(event) => setName(event.target.value)} />
          <FormControlLabel
            control={<Checkbox checked={includeWorkspace} onChange={(event) => setIncludeWorkspace(event.target.checked)} />}
            label="Include workspace template"
          />
        </Box>
        {preview ? (
          <Typography variant="body2" color="text.secondary">
            {preview.pins} pins, {preview.cron_jobs} cron jobs, {preview.playbooks.length} playbooks, {preview.agent_apps.length} Agent Apps, {preview.secrets.length} secret keys.
          </Typography>
        ) : null}
        <Button disabled={busy} variant="contained" startIcon={<DownloadIcon />} onClick={() => void exportKit()}>
          Export client kit
        </Button>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="h6">Import</Typography>
        <Button component="label" variant="outlined" startIcon={<UploadIcon />}>
          Import kit
          <input hidden type="file" accept=".zip" onChange={(event) => void importKit(event.currentTarget.files?.[0] ?? null)} />
        </Button>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 1 }}>
        <Typography variant="h6">Simplified mode</Typography>
        <FormControlLabel
          control={<Switch checked={Boolean(simplified?.simplified_mode)} onChange={(event) => void updateSimplified({ simplified_mode: event.target.checked })} />}
          label="Enable simplified mode"
        />
        <FormControlLabel
          control={<Switch checked={Boolean(simplified?.hide_terminal_coding)} onChange={(event) => void updateSimplified({ hide_terminal_coding: event.target.checked })} />}
          label="Hide terminal and coding surfaces"
        />
        <FormControlLabel
          control={<Switch checked={Boolean(simplified?.documents_read_only)} onChange={(event) => void updateSimplified({ documents_read_only: event.target.checked })} />}
          label="Documents read-only"
        />
      </Paper>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}

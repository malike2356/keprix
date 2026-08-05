"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PauseCircleIcon from "@mui/icons-material/PauseCircle";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import SaveIcon from "@mui/icons-material/Save";
import SyncIcon from "@mui/icons-material/Sync";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";

type Status = {
  enabled: boolean;
  configured: boolean;
  connected?: boolean;
  has_api_key?: boolean;
  hasApiKey?: boolean;
  base_url?: string;
  baseUrl?: string;
  folder_id?: string;
  folderId?: string;
  folder_label?: string;
  folderLabel?: string;
  vault_path?: string;
  vaultPath?: string;
  syncthing_path?: string;
  syncthingPath?: string;
  writer_role?: string;
  writerRole?: string;
  folder_type?: string;
  folderType?: string;
  device_ids?: string[];
  deviceIds?: string[];
  rescan_interval_s?: number;
  rescanIntervalS?: number;
  last_error?: string | null;
  lastError?: string | null;
  last_ok_at?: string | null;
  lastOkAt?: string | null;
  warnings?: string[];
  one_writer?: { summary?: string; local_folder_type?: string; keprix_vault_read_only?: boolean };
  oneWriter?: { summary?: string; local_folder_type?: string; keprix_vault_read_only?: boolean };
  syncthing?: { myId?: string; my_id?: string; version?: string } | null;
  folder?: Record<string, unknown> | null;
  ok?: boolean;
  error?: string;
};

const fetcher = async (url: string): Promise<Status> => {
  const response = await ceApi(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

export default function SyncthingSettingsPage() {
  const { data, error, mutate } = useSWR("/api/syncthing/status", fetcher);
  const [message, setMessage] = React.useState<string | null>(null);
  const [enabled, setEnabled] = React.useState(false);
  const [baseUrl, setBaseUrl] = React.useState("http://syncthing:8384");
  const [folderId, setFolderId] = React.useState("keprix-obsidian-vault");
  const [folderLabel, setFolderLabel] = React.useState("Keprix Obsidian Vault");
  const [vaultPath, setVaultPath] = React.useState("");
  const [syncthingPath, setSyncthingPath] = React.useState("/var/syncthing/vault");
  const [writerRole, setWriterRole] = React.useState("home");
  const [deviceIds, setDeviceIds] = React.useState("");
  const [rescanIntervalS, setRescanIntervalS] = React.useState(60);
  const [apiKey, setApiKey] = React.useState("");
  const [clearKey, setClearKey] = React.useState(false);

  React.useEffect(() => {
    if (!data) return;
    setEnabled(Boolean(data.enabled));
    setBaseUrl(data.base_url ?? data.baseUrl ?? "http://syncthing:8384");
    setFolderId(data.folder_id ?? data.folderId ?? "keprix-obsidian-vault");
    setFolderLabel(data.folder_label ?? data.folderLabel ?? "Keprix Obsidian Vault");
    setVaultPath(data.vault_path ?? data.vaultPath ?? "");
    setSyncthingPath(data.syncthing_path ?? data.syncthingPath ?? "");
    setWriterRole(data.writer_role ?? data.writerRole ?? "home");
    const devices = data.device_ids ?? data.deviceIds ?? [];
    setDeviceIds(devices.join(", "));
    setRescanIntervalS(data.rescan_interval_s ?? data.rescanIntervalS ?? 60);
  }, [data]);

  async function save() {
    const payload: Record<string, unknown> = {
      enabled,
      baseUrl,
      folderId,
      folderLabel,
      vaultPath,
      syncthingPath,
      writerRole,
      deviceIds: deviceIds
        .split(/[,\n]/)
        .map((item) => item.trim())
        .filter(Boolean),
      rescanIntervalS,
    };
    if (clearKey) payload.apiKey = null;
    else if (apiKey.trim()) payload.apiKey = apiKey.trim();

    const response = await ceApi("/api/syncthing/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok || body.ok === false) {
      setMessage(typeof body.detail === "string" ? body.detail : body.error || "Save failed");
      void mutate();
      return;
    }
    setApiKey("");
    setClearKey(false);
    setMessage("Saved. One-writer role applied to vault folder type.");
    void mutate();
  }

  async function ensureFolder() {
    const response = await ceApi("/api/syncthing/ensure-folder", {
      method: "POST",
    });
    const body = await response.json();
    setMessage(body.ok ? `Folder ready (${body.folder_type || body.folderType})` : body.detail || body.error || "Ensure failed");
    void mutate();
  }

  async function setPaused(paused: boolean) {
    const response = await ceApi("/api/syncthing/pause", {
      method: "POST",
      body: JSON.stringify({ paused }),
    });
    const body = await response.json();
    setMessage(body.ok ? (paused ? "Folder paused" : "Folder resumed") : body.detail || body.error || "Pause failed");
    void mutate();
  }

  const hasKey = Boolean(data?.has_api_key ?? data?.hasApiKey);
  const lastError = data?.last_error ?? data?.lastError;
  const oneWriter = data?.one_writer ?? data?.oneWriter;
  const warnings = data?.warnings || [];
  const myId = data?.syncthing?.myId ?? data?.syncthing?.my_id;

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Syncthing (Obsidian vault)"
        description="Sync the Obsidian vault only. GitHub agent-sync owns memory and skills. Pick one writer."
      />
      {message ? (
        <Alert severity={/fail|error|overlap|WARNING/i.test(message) ? "warning" : "info"} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? <Alert severity="error">Failed to load Syncthing status. Sign in and retry.</Alert> : null}
      {lastError ? <Alert severity="warning">Last error: {lastError}</Alert> : null}
      {warnings.map((warning) => (
        <Alert key={warning} severity="warning">
          {warning}
        </Alert>
      ))}

      <Paper variant="outlined" sx={{ p: 2, display: "grid", gap: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Chip color={data?.enabled ? "success" : "default"} label={data?.enabled ? "Enabled" : "Disabled"} />
          <Chip variant="outlined" label={hasKey ? "API key saved" : "API key needed"} color={hasKey ? "success" : "warning"} />
          <Chip variant="outlined" label={data?.connected ? "Connected" : "Not connected"} color={data?.connected ? "success" : "default"} />
          <Chip variant="outlined" label={`Folder: ${data?.folder_type ?? data?.folderType ?? "receiveonly"}`} />
        </Stack>
        <Typography variant="body2" color="text.secondary">
          Start the sidecar with{" "}
          <code>COMPOSE_FILE=docker/docker-compose.yml:docker/docker-compose.syncthing.yml docker compose up -d syncthing</code>.
          Open Syncthing GUI on host port 8384, copy the API key, paste below. From containers use base URL{" "}
          <code>http://syncthing:8384</code>. Syncthing path on the sidecar is usually <code>/var/syncthing/vault</code>; Keprix vault path stays under{" "}
          <code>/home/keprix/.keprix/vault</code> (same host bind).
        </Typography>
        {oneWriter?.summary ? (
          <Alert severity={writerRole === "both" ? "warning" : "info"}>{oneWriter.summary}</Alert>
        ) : null}
        {myId ? (
          <Typography variant="caption" color="text.secondary">
            This Syncthing device ID: {myId}
            {data?.syncthing?.version ? ` (v${data.syncthing.version})` : ""}
          </Typography>
        ) : null}

        <FormControlLabel
          control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
          label="Enable Obsidian vault Syncthing bridge"
        />

        <TextField
          label="Syncthing base URL"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          helperText="Docker network: http://syncthing:8384. Host process: http://127.0.0.1:8384"
          fullWidth
        />
        <TextField
          label="API key"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={hasKey ? "Leave blank to keep saved key" : "Paste from Syncthing Actions"}
          fullWidth
        />
        <FormControlLabel
          control={<Switch checked={clearKey} onChange={(e) => setClearKey(e.target.checked)} />}
          label="Clear saved API key on save"
        />

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField label="Folder ID" value={folderId} onChange={(e) => setFolderId(e.target.value)} fullWidth />
          <TextField label="Folder label" value={folderLabel} onChange={(e) => setFolderLabel(e.target.value)} fullWidth />
        </Stack>

        <TextField
          label="Keprix vault path"
          value={vaultPath}
          onChange={(e) => setVaultPath(e.target.value)}
          helperText="Path as Keprix sees it. Must NOT be the github-agent-sync clone."
          fullWidth
        />
        <TextField
          label="Syncthing filesystem path"
          value={syncthingPath}
          onChange={(e) => setSyncthingPath(e.target.value)}
          helperText="Path as the Syncthing process sees it (sidecar: /var/syncthing/vault)."
          fullWidth
        />

        <TextField
          select
          label="One writer"
          value={writerRole}
          onChange={(e) => setWriterRole(e.target.value)}
          helperText="home = Obsidian writes, Keprix receive-only. keprix = Keprix writes. both = conflicts likely."
          fullWidth
        >
          <MenuItem value="home">home (Obsidian primary writer)</MenuItem>
          <MenuItem value="keprix">keprix (Keprix primary writer)</MenuItem>
          <MenuItem value="both">both (not recommended)</MenuItem>
        </TextField>

        <TextField
          label="Peer device IDs"
          value={deviceIds}
          onChange={(e) => setDeviceIds(e.target.value)}
          helperText="Comma-separated Syncthing device IDs to share the vault folder with (home PC, phone)."
          fullWidth
          multiline
          minRows={2}
        />
        <TextField
          label="Rescan interval (seconds)"
          type="number"
          value={rescanIntervalS}
          onChange={(e) => setRescanIntervalS(Number(e.target.value) || 60)}
          fullWidth
        />

        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="contained" startIcon={<SaveIcon />} onClick={() => void save()}>
            Save
          </Button>
          <Button variant="outlined" startIcon={<SyncIcon />} onClick={() => void ensureFolder()}>
            Ensure folder
          </Button>
          <Button variant="outlined" startIcon={<PauseCircleIcon />} onClick={() => void setPaused(true)}>
            Pause
          </Button>
          <Button variant="outlined" startIcon={<PlayCircleIcon />} onClick={() => void setPaused(false)}>
            Resume
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Separation rule
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Syncthing = Obsidian vault markdown notes. Agent-sync (Settings -&gt; Agent sync) = shared memory and skills over GitHub.
          Do not point both at the same write-heavy tree. Enabling Syncthing on an agent-sync path is blocked.
        </Typography>
      </Paper>
    </Box>
  );
}

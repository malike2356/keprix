"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  connectZotero,
  fetchZoteroSettings,
  importZoteroBibTeX,
  type ZoteroSettings,
} from "@/lib/research-workspace-api";

type Props = {
  projectId: string | null;
  onConnected?: () => void;
};

export default function ZoteroSettings({ projectId, onConnected }: Props) {
  const [settings, setSettings] = React.useState<ZoteroSettings | null>(null);
  const [mode, setMode] = React.useState("web");
  const [apiKey, setApiKey] = React.useState("");
  const [libraryId, setLibraryId] = React.useState("");
  const [bibtex, setBibtex] = React.useState("");
  const [importFormat, setImportFormat] = React.useState<"bibtex" | "better-bibtex">("better-bibtex");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetchZoteroSettings()
      .then((payload) => setSettings(payload.settings))
      .catch(() => setSettings(null));
  }, []);

  const connect = async () => {
    setError(null);
    try {
      const payload = await connectZotero({
        mode: mode as "web" | "local" | "file",
        api_key: mode === "web" ? apiKey : undefined,
        library_id: libraryId || undefined,
      });
      setSettings(payload.settings);
      setMessage("Zotero library connected. API key stored in vault.");
      onConnected?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connect failed");
    }
  };

  const importFile = async () => {
    if (!projectId || !bibtex.trim()) return;
    setError(null);
    try {
      const result = await importZoteroBibTeX({
        project_id: projectId,
        content: bibtex,
        format: importFormat,
      });
      setMessage(`Imported ${result.imported} citations.`);
      onConnected?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Zotero citations</Typography>
      <Typography variant="caption" color="text.secondary">
        Web API, local connector, or Better BibTeX file import. Keys are stored in the vault.
      </Typography>
      {settings?.connected ? (
        <Typography variant="caption" color="text.secondary">
          Connected ({settings.mode})
          {settings.library_id ? ` | library ${settings.library_id}` : ""}
        </Typography>
      ) : null}
      <FormControl size="small" fullWidth>
        <InputLabel id="zotero-mode-label">Mode</InputLabel>
        <Select labelId="zotero-mode-label" label="Mode" value={mode} onChange={(e) => setMode(String(e.target.value))}>
          <MenuItem value="web">Zotero Web API</MenuItem>
          <MenuItem value="local">Zotero local API</MenuItem>
          <MenuItem value="file">BibTeX file only</MenuItem>
        </Select>
      </FormControl>
      {mode === "web" ? (
        <>
          <TextField
            size="small"
            label="API key"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <TextField
            size="small"
            label="Library ID"
            value={libraryId}
            onChange={(e) => setLibraryId(e.target.value)}
          />
          <Button size="small" variant="contained" onClick={connect} disabled={!apiKey || !libraryId}>
            Connect Zotero
          </Button>
        </>
      ) : (
        <Button size="small" variant="contained" onClick={connect}>
          Save {mode} mode
        </Button>
      )}
      <FormControl size="small" fullWidth>
        <InputLabel id="bibtex-format-label">Import format</InputLabel>
        <Select
          labelId="bibtex-format-label"
          label="Import format"
          value={importFormat}
          onChange={(e) => setImportFormat(e.target.value as "bibtex" | "better-bibtex")}
        >
          <MenuItem value="bibtex">BibTeX</MenuItem>
          <MenuItem value="better-bibtex">Better BibTeX</MenuItem>
        </Select>
      </FormControl>
      <TextField
        size="small"
        label="BibTeX paste"
        value={bibtex}
        onChange={(e) => setBibtex(e.target.value)}
        multiline
        minRows={4}
      />
      <Button size="small" variant="outlined" onClick={importFile} disabled={!projectId || !bibtex.trim()}>
        Import citations
      </Button>
      {message ? (
        <Typography variant="body2" color="text.secondary">
          {message}
        </Typography>
      ) : null}
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}
    </Box>
  );
}

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
  exportResearchObsidian,
  indexObsidianVault,
  listObsidianVaults,
  registerObsidianVault,
  type ObsidianVault,
} from "@/lib/research-workspace-api";

type Props = {
  projectId?: string | null;
  onVaultSelected?: (vaultId: string | null) => void;
  onExported?: () => void;
};

export default function ObsidianVaultSettings({ projectId, onVaultSelected, onExported }: Props) {
  const [vaults, setVaults] = React.useState<ObsidianVault[]>([]);
  const [name, setName] = React.useState("Research vault");
  const [localPath, setLocalPath] = React.useState("");
  const [syncMode, setSyncMode] = React.useState("write-draft");
  const [allowExternal, setAllowExternal] = React.useState(false);
  const [selectedId, setSelectedId] = React.useState<string>("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(() => {
    listObsidianVaults()
      .then((payload) => setVaults(payload.items))
      .catch(() => setVaults([]));
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  React.useEffect(() => {
    onVaultSelected?.(selectedId || null);
  }, [onVaultSelected, selectedId]);

  const register = async () => {
    setError(null);
    setMessage(null);
    try {
      const result = await registerObsidianVault({
        name,
        local_path: localPath,
        sync_mode: syncMode,
        allow_external_path: allowExternal,
      });
      setSelectedId(result.vault.vault_id);
      setMessage(`Registered vault at ${result.vault.local_path}`);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  };

  const indexVault = async () => {
    if (!selectedId) return;
    setError(null);
    try {
      const result = await indexObsidianVault(selectedId);
      setMessage(`Indexed ${result.note_count} notes. Obsidian does not need to be open.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Index failed");
    }
  };

  const exportProject = async () => {
    if (!projectId) return;
    setError(null);
    setMessage(null);
    try {
      const result = await exportResearchObsidian(projectId);
      setMessage(`Exported ${result.files} note file(s) to your vault. Open Obsidian to browse the graph.`);
      onExported?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Obsidian notes</Typography>
      <Typography variant="caption" color="text.secondary">
        Point Keprix at your Obsidian vault folder. Notes sync through the filesystem; the Obsidian app can stay
        closed while Keprix writes drafts.
      </Typography>
      {vaults.length ? (
        <FormControl size="small" fullWidth>
          <InputLabel id="vault-select-label">Registered vault</InputLabel>
          <Select
            labelId="vault-select-label"
            label="Registered vault"
            value={selectedId}
            onChange={(event) => setSelectedId(String(event.target.value))}
          >
            {vaults.map((vault) => (
              <MenuItem key={vault.vault_id} value={vault.vault_id}>
                {vault.name} ({vault.sync_mode})
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : null}
      <TextField size="small" label="Vault name" value={name} onChange={(e) => setName(e.target.value)} />
      <TextField
        size="small"
        label="Vault folder path"
        value={localPath}
        onChange={(e) => setLocalPath(e.target.value)}
        placeholder="/home/you/Documents/ResearchVault"
        helperText="Absolute path or workspace-relative folder where Obsidian stores markdown files"
      />
      <FormControl size="small" fullWidth>
        <InputLabel id="sync-mode-label">Sync mode</InputLabel>
        <Select
          labelId="sync-mode-label"
          label="Sync mode"
          value={syncMode}
          onChange={(e) => setSyncMode(String(e.target.value))}
        >
          <MenuItem value="read-only">read-only</MenuItem>
          <MenuItem value="write-draft">write-draft</MenuItem>
          <MenuItem value="write-approved">write-approved</MenuItem>
        </Select>
      </FormControl>
      <FormControl size="small" fullWidth>
        <InputLabel id="external-path-label">External path</InputLabel>
        <Select
          labelId="external-path-label"
          label="External path"
          value={allowExternal ? "yes" : "no"}
          onChange={(e) => setAllowExternal(e.target.value === "yes")}
        >
          <MenuItem value="no">Workspace storage only</MenuItem>
          <MenuItem value="yes">Allow external path</MenuItem>
        </Select>
      </FormControl>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        <Button size="small" variant="contained" onClick={register} disabled={!localPath.trim()}>
          Save vault
        </Button>
        <Button size="small" variant="outlined" onClick={indexVault} disabled={!selectedId}>
          Refresh index
        </Button>
        {projectId ? (
          <Button size="small" variant="outlined" onClick={exportProject}>
            Export project notes
          </Button>
        ) : null}
      </Box>
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

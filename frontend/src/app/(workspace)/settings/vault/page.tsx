"use client";

import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import SaveIcon from "@mui/icons-material/Save";
import SearchIcon from "@mui/icons-material/Search";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { ceApi } from "@/lib/ce-api";
import { listVaultFiles, type VaultFile } from "@/lib/vault-api";

type VaultConfig = {
  provider: string;
  root_path: string;
  watch: boolean;
  read_only: boolean;
};

const defaults: VaultConfig = { provider: "local_folder", root_path: "", watch: true, read_only: false };

export default function VaultSettingsPage() {
  const [config, setConfig] = React.useState<VaultConfig>(defaults);
  const [files, setFiles] = React.useState<VaultFile[]>([]);
  const [query, setQuery] = React.useState("");
  const [graph, setGraph] = React.useState<{ nodes: unknown[]; edges: unknown[] } | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    void (async () => {
      const response = await ceApi("/api/vault/config");
      if (!response.ok) return;
      const payload = (await response.json()) as { config: VaultConfig };
      setConfig(payload.config);
    })();
  }, []);

  const save = async () => {
    const response = await ceApi("/api/vault/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    setMessage(response.ok ? "Vault connected." : "Connection failed.");
    if (response.ok) await listFiles();
  };

  const listFiles = async () => {
    try {
      setFiles(await listVaultFiles());
    } catch {
      setMessage("Vault is not configured or the path is unavailable.");
    }
  };

  const search = async () => {
    const response = await ceApi(`/api/vault/search?query=${encodeURIComponent(query)}`);
    if (!response.ok) return;
    const payload = (await response.json()) as { results: VaultFile[] };
    setFiles(payload.results);
  };

  const loadGraph = async () => {
    const response = await ceApi("/api/vault/graph");
    if (!response.ok) return;
    setGraph((await response.json()) as { nodes: unknown[]; edges: unknown[] });
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="Knowledge vault"
        description="Use any markdown folder as the agent knowledge base."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Vault" },
        ]}
      />
      <Box sx={{ display: "grid", gap: 2, maxWidth: 760 }}>
        <TextField select label="Provider" value={config.provider} onChange={(event) => setConfig({ ...config, provider: event.target.value })}>
          <MenuItem value="local_folder">Local folder</MenuItem>
          <MenuItem value="obsidian">Obsidian vault</MenuItem>
        </TextField>
        <TextField label="Root path" value={config.root_path} onChange={(event) => setConfig({ ...config, root_path: event.target.value })} />
        <FormControlLabel
          control={<Checkbox checked={config.watch} onChange={(event) => setConfig({ ...config, watch: event.target.checked })} />}
          label="Watch for changes"
        />
        <FormControlLabel
          control={<Checkbox checked={config.read_only} onChange={(event) => setConfig({ ...config, read_only: event.target.checked })} />}
          label="Read-only"
        />
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button variant="contained" startIcon={<SaveIcon />} onClick={() => void save()}>
            Save and test
          </Button>
          <Button startIcon={<FolderOpenIcon />} onClick={() => void listFiles()}>
            List files
          </Button>
          <Button onClick={() => void loadGraph()}>Graph</Button>
        </Box>
      </Box>
      <Box sx={{ display: "flex", gap: 1, maxWidth: 760 }}>
        <TextField fullWidth label="Search" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Button startIcon={<SearchIcon />} onClick={() => void search()}>
          Search
        </Button>
      </Box>
      {graph && (
        <Typography variant="body2" color="text.secondary">
          Graph: {graph.nodes.length} node(s), {graph.edges.length} edge(s)
        </Typography>
      )}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Path</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Size</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {files.map((file) => (
            <TableRow key={file.path}>
              <TableCell>{file.path}</TableCell>
              <TableCell>{file.is_dir ? "Folder" : "File"}</TableCell>
              <TableCell>{file.size}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}

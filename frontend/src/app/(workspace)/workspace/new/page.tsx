"use client";

import AddIcon from "@mui/icons-material/Add";
import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
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

type Template = {
  id: string;
  name: string;
  description: string;
  folders: string[];
};

type Workspace = {
  id: string;
  name: string;
  path: string;
};

export default function NewWorkspacePage() {
  const [templates, setTemplates] = React.useState<Template[]>([]);
  const [templateId, setTemplateId] = React.useState("knowledge_pipeline");
  const [name, setName] = React.useState("knowledge-hub");
  const [workspace, setWorkspace] = React.useState<Workspace | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const loadTemplates = React.useCallback(async () => {
    const response = await ceApi("/api/workspaces/templates");
    if (!response.ok) {
      setMessage("Failed to load templates.");
      return;
    }
    const payload = (await response.json()) as { templates: Template[] };
    setTemplates(payload.templates);
  }, []);

  React.useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  const create = async () => {
    setBusy(true);
    try {
      const response = await ceApi("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, template_id: templateId }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { workspace: Workspace };
      setWorkspace(payload.workspace);
      setMessage("Workspace created with indexes and KEPRIX.md.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const reindex = async () => {
    if (!workspace) return;
    setBusy(true);
    try {
      const response = await ceApi(`/api/workspaces/${workspace.id}/reindex`, { method: "POST" });
      setMessage(response.ok ? "Indexes regenerated." : "Reindex failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 3 }}>
      <PageHeader
        title="New workspace"
        description="Create a structured memory workspace with folders, indexes, and KEPRIX.md."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "New workspace" },
        ]}
      />
      <Box sx={{ display: "grid", gap: 2, maxWidth: 720 }}>
        <TextField label="Workspace name" value={name} onChange={(event) => setName(event.target.value)} />
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {templates.map((template) => (
            <Chip
              key={template.id}
              label={template.name}
              color={templateId === template.id ? "primary" : "default"}
              onClick={() => setTemplateId(template.id)}
            />
          ))}
        </Box>
        <Button disabled={busy || !name.trim()} variant="contained" startIcon={<AddIcon />} onClick={() => void create()}>
          Create workspace
        </Button>
      </Box>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Template</TableCell>
            <TableCell>Folders</TableCell>
            <TableCell>Description</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {templates.map((template) => (
            <TableRow key={template.id}>
              <TableCell>{template.name}</TableCell>
              <TableCell>{template.folders.join(", ") || "Custom"}</TableCell>
              <TableCell>{template.description}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {workspace && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="body2" color="text.secondary">
            {workspace.path}
          </Typography>
          <Button disabled={busy} startIcon={<RefreshIcon />} onClick={() => void reindex()}>
            Reindex
          </Button>
        </Box>
      )}
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
}

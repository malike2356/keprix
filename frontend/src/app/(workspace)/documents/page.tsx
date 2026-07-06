"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import FolderIcon from "@mui/icons-material/Folder";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonDetailPanel, SkeletonList } from "@/components/ui/loading";
import {
  createDocument,
  deleteDocument,
  fetchDocuments,
  updateDocument,
  type WorkspaceDocument,
} from "@/lib/workspace-api";

export default function DocumentsPage() {
  const [documents, setDocuments] = React.useState<WorkspaceDocument[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  const selected = documents.find((doc) => doc.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchDocuments();
      setDocuments(items);
      if (!selectedId && items.length > 0) {
        setSelectedId(items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  React.useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const doc = await createDocument({ title: title.trim(), content });
      setDocuments((prev) => [doc, ...prev]);
      setSelectedId(doc.id);
      setDialogOpen(false);
      setTitle("");
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create document");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveSelected() {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await updateDocument(selected.id, {
        title: selected.title,
        content: selected.content,
      });
      setDocuments((prev) => prev.map((doc) => (doc.id === updated.id ? updated : doc)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save document");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSelected() {
    if (!selected) return;
    setSaving(true);
    try {
      await deleteDocument(selected.id);
      const remaining = documents.filter((doc) => doc.id !== selected.id);
      setDocuments(remaining);
      setSelectedId(remaining[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete document");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Box>
      <PageHeader
        title="Documents"
        description="Create and edit markdown workspace documents."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Documents", href: "/documents" },
        ]}
        actions={
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            New document
          </Button>
        }
      />
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      {loading ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "280px 1fr" }, gap: 2 }}>
          <SkeletonList rows={8} rowHeight={48} />
          <SkeletonDetailPanel fields={4} />
        </Box>
      ) : documents.length === 0 ? (
        <EmptyState
          title="No documents"
          description="Create a document to capture longer-form workspace content."
          icon={<FolderIcon sx={{ fontSize: 48 }} />}
          actionLabel="New document"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "280px 1fr" }, gap: 2 }}>
          <List dense sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
            {documents.map((doc) => (
              <ListItemButton key={doc.id} selected={doc.id === selectedId} onClick={() => setSelectedId(doc.id)}>
                <ListItemText
                  primary={doc.title || "Untitled"}
                  secondary={`${doc.word_count ?? 0} words`}
                />
              </ListItemButton>
            ))}
          </List>
          {selected && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="Title"
                value={selected.title}
                onChange={(e) =>
                  setDocuments((prev) =>
                    prev.map((doc) => (doc.id === selected.id ? { ...doc, title: e.target.value } : doc)),
                  )
                }
              />
              <TextField
                label="Content"
                value={selected.content}
                onChange={(e) =>
                  setDocuments((prev) =>
                    prev.map((doc) => (doc.id === selected.id ? { ...doc, content: e.target.value } : doc)),
                  )
                }
                multiline
                minRows={14}
              />
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button variant="contained" onClick={handleSaveSelected} disabled={saving}>
                  Save
                </Button>
                <Button variant="outlined" color="error" onClick={handleDeleteSelected} disabled={saving}>
                  Delete
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      )}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New document</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <TextField
            label="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            multiline
            minRows={6}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving || !title.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

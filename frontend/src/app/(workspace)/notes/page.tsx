"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NotesIcon from "@mui/icons-material/Notes";
import PushPinIcon from "@mui/icons-material/PushPin";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import { createNote, deleteNote, fetchNotes, type WorkspaceNote } from "@/lib/workspace-api";

export default function NotesPage() {
  const [query, setQuery] = React.useState("");
  const [notes, setNotes] = React.useState<WorkspaceNote[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  const load = React.useCallback(async (search?: string) => {
    setLoading(true);
    setError(null);
    try {
      setNotes(await fetchNotes(search));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load notes");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  React.useEffect(() => {
    const timer = setTimeout(() => load(query || undefined), 250);
    return () => clearTimeout(timer);
  }, [query, load]);

  async function handleCreate() {
    if (!title.trim() && !content.trim()) return;
    setSaving(true);
    try {
      const note = await createNote({ title: title.trim(), content });
      setNotes((prev) => [note, ...prev]);
      setDialogOpen(false);
      setTitle("");
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create note");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteNote(id);
      setNotes((prev) => prev.filter((note) => note.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete note");
    }
  }

  return (
    <Box>
      <PageHeader
        title="Notes"
        description="Capture linked notes and references."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Notes", href: "/notes" },
        ]}
        actions={
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            New note
          </Button>
        }
      />
      <TextField
        fullWidth
        size="small"
        placeholder="Search notes..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 2 }}
      />
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      {loading ? (
        <SkeletonList rows={6} />
      ) : notes.length === 0 ? (
        <EmptyState
          title="No notes yet"
          description="Create a note to capture ideas and references."
          icon={<NotesIcon sx={{ fontSize: 48 }} />}
          actionLabel="New note"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <List sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
          {notes.map((note) => (
            <ListItem
              key={note.id}
              secondaryAction={
                <Button size="small" color="error" onClick={() => handleDelete(note.id)}>
                  Delete
                </Button>
              }
              alignItems="flex-start"
            >
              <ListItemText
                primary={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {note.is_pinned && <PushPinIcon fontSize="small" color="primary" />}
                    <Typography component="span" fontWeight={600}>
                      {note.title || "Untitled note"}
                    </Typography>
                  </Box>
                }
                secondary={
                  <Box sx={{ mt: 0.5 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "pre-wrap" }}>
                      {note.content || "(empty)"}
                    </Typography>
                    {note.tags?.length > 0 && (
                      <Box sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                        {note.tags.map((tag) => (
                          <Chip key={tag} size="small" label={tag} />
                        ))}
                      </Box>
                    )}
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      )}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New note</DialogTitle>
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
          <Button variant="contained" onClick={handleCreate} disabled={saving}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

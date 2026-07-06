"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createObsidianDraftNote,
  fetchObsidianBacklinks,
  type ObsidianIndexedNote,
} from "@/lib/research-workspace-api";

const NOTE_TYPES = [
  "literature",
  "source",
  "claim",
  "dataset",
  "meeting",
  "field",
  "research_summary",
] as const;

type Props = {
  projectId: string | null;
  vaultId: string | null;
};

export default function LinkedNotesPanel({ projectId, vaultId }: Props) {
  const [noteType, setNoteType] = React.useState<string>("literature");
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [notes, setNotes] = React.useState<ObsidianIndexedNote[]>([]);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const loadBacklinks = React.useCallback(async () => {
    if (!projectId || !vaultId) {
      setNotes([]);
      return;
    }
    try {
      const payload = await fetchObsidianBacklinks(projectId, vaultId);
      setNotes(payload.items);
    } catch {
      setNotes([]);
    }
  }, [projectId, vaultId]);

  React.useEffect(() => {
    loadBacklinks();
  }, [loadBacklinks]);

  const createDraft = async () => {
    if (!projectId || !vaultId) return;
    setError(null);
    try {
      await createObsidianDraftNote(projectId, {
        vault_id: vaultId,
        note_type: noteType,
        title,
        body,
        backlinks: ["index"],
      });
      setMessage(`Draft ${noteType} note created with provenance frontmatter.`);
      setTitle("");
      setBody("");
      await loadBacklinks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft creation failed");
    }
  };

  if (!projectId) {
    return (
      <Typography variant="body2" color="text.secondary">
        Select a project to manage linked Obsidian notes.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Typography variant="subtitle2">Linked notes</Typography>
      {!vaultId ? (
        <Typography variant="caption" color="text.secondary">
          Register or select an Obsidian vault first.
        </Typography>
      ) : (
        <>
          <FormControl size="small" fullWidth>
            <InputLabel id="note-type-label">Note type</InputLabel>
            <Select
              labelId="note-type-label"
              label="Note type"
              value={noteType}
              onChange={(e) => setNoteType(String(e.target.value))}
            >
              {NOTE_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField size="small" label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextField
            size="small"
            label="Body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            multiline
            minRows={3}
          />
          <Button
            size="small"
            variant="outlined"
            onClick={createDraft}
            disabled={!title.trim()}
          >
            Create draft note
          </Button>
        </>
      )}
      {notes.length ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {notes.slice(0, 6).map((note) => (
            <Box key={note.path} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1 }}>
              <Typography variant="caption">{note.title}</Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                {note.tags?.slice(0, 4).map((tag) => (
                  <Chip key={tag} size="small" label={`#${tag}`} />
                ))}
              </Box>
              {note.backlinks?.length ? (
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                  backlinks: {note.backlinks.join(", ")}
                </Typography>
              ) : null}
            </Box>
          ))}
        </Box>
      ) : null}
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

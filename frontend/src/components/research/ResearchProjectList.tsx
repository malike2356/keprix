"use client";

import AddIcon from "@mui/icons-material/Add";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import {
  createResearchProject,
  fetchResearchProjects,
  type ResearchProject,
} from "@/lib/research-workspace-api";

type Props = {
  selectedId: string | null;
  onSelect: (projectId: string) => void;
  onCreated?: (project: ResearchProject) => void;
};

export default function ResearchProjectList({ selectedId, onSelect, onCreated }: Props) {
  const [projects, setProjects] = React.useState<ResearchProject[]>([]);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("Field study");
  const [question, setQuestion] = React.useState("What evidence supports the primary claim?");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(() => {
    fetchResearchProjects()
      .then((payload) => setProjects(payload.items || []))
      .catch((err: Error) => setError(err.message));
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const onCreate = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await createResearchProject({ title, question });
      onCreated?.(result.project);
      onSelect(result.project.project_id);
      setDialogOpen(false);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent sx={{ pb: 1 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
          <Typography variant="subtitle1">Projects</Typography>
          <Button size="small" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
            New
          </Button>
        </Stack>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mb: 1 }}>
            {error}
          </Typography>
        ) : null}
        <List dense disablePadding>
          {projects.map((project) => (
            <ListItemButton
              key={project.project_id}
              selected={selectedId === project.project_id}
              onClick={() => onSelect(project.project_id)}
              sx={{ borderRadius: 1, mb: 0.5 }}
            >
              <ListItemText
                primary={project.title}
                secondary={project.question || project.project_id}
                primaryTypographyProps={{ noWrap: true }}
                secondaryTypographyProps={{ noWrap: true }}
              />
              <IconButton
                component="a"
                href={`/research/projects/${project.project_id}`}
                size="small"
                aria-label="Open project page"
                onClick={(event) => event.stopPropagation()}
              >
                <OpenInNewIcon fontSize="small" />
              </IconButton>
            </ListItemButton>
          ))}
          {!projects.length ? (
            <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
              No projects yet.
            </Typography>
          ) : null}
        </List>
      </CardContent>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New research project</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "grid", gap: 2, pt: 1 }}>
            <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
            <TextField
              label="Research question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              multiline
              minRows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={onCreate} disabled={busy || !title.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}

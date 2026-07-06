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
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import { completeTask, createTask, fetchTasks, type WorkspaceTask } from "@/lib/workspace-api";

const STATUS_TABS = [
  { value: "todo", label: "To do" },
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
] as const;

type TaskStatus = (typeof STATUS_TABS)[number]["value"];

export default function TasksPage() {
  const [status, setStatus] = React.useState<TaskStatus>("todo");
  const [tasks, setTasks] = React.useState<WorkspaceTask[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTasks(await fetchTasks(status));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [status]);

  React.useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const task = await createTask({ title: title.trim(), description, status });
      setTasks((prev) => [task, ...prev]);
      setDialogOpen(false);
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setSaving(false);
    }
  }

  async function handleComplete(taskId: string) {
    try {
      const updated = await completeTask(taskId);
      setTasks((prev) => prev.filter((task) => task.id !== updated.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete task");
    }
  }

  return (
    <Box>
      <PageHeader
        title="Tasks"
        description="Track work items and follow-ups."
        breadcrumbs={[
          { label: "Workspace", href: "/launcher" },
          { label: "Tasks", href: "/tasks" },
        ]}
        actions={
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            New task
          </Button>
        }
      />
      <Tabs value={status} onChange={(_e, value) => setStatus(value as TaskStatus)} sx={{ mb: 2 }}>
        {STATUS_TABS.map((tab) => (
          <Tab key={tab.value} value={tab.value} label={tab.label} />
        ))}
      </Tabs>
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}
      {loading ? (
        <SkeletonList rows={6} />
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No tasks"
          description="Add tasks to track work across your workspace."
          icon={<TaskAltIcon sx={{ fontSize: 48 }} />}
          actionLabel="New task"
          onAction={() => setDialogOpen(true)}
        />
      ) : (
        <List sx={{ bgcolor: "background.paper", borderRadius: 1, border: 1, borderColor: "divider" }}>
          {tasks.map((task) => (
            <ListItem
              key={task.id}
              secondaryAction={
                status !== "done" ? (
                  <Button size="small" onClick={() => handleComplete(task.id)}>
                    Complete
                  </Button>
                ) : null
              }
            >
              <ListItemText
                primary={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                    <Typography component="span" fontWeight={600}>
                      {task.title}
                    </Typography>
                    <Chip size="small" label={task.priority} />
                    {task.agent_scheduled && (
                      <Chip size="small" icon={<SmartToyIcon />} label="Agent" color="info" variant="outlined" />
                    )}
                  </Box>
                }
                secondary={task.description || undefined}
              />
            </ListItem>
          ))}
        </List>
      )}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>New task</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            minRows={3}
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

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import {
  createTask,
  deleteTask,
  fetchTasks,
  reorderTasks,
  updateTask,
  type WorkspaceTask,
} from "@/lib/workspace-api";

const COLUMNS = [
  { value: "todo", label: "To do", wipLimit: null as number | null },
  { value: "in_progress", label: "In progress", wipLimit: 5 },
  { value: "done", label: "Done", wipLimit: null as number | null },
] as const;

type TaskStatus = (typeof COLUMNS)[number]["value"];

const PRIORITIES = ["low", "normal", "high", "urgent"] as const;

type BoardState = Record<TaskStatus, WorkspaceTask[]>;

type TaskForm = {
  title: string;
  description: string;
  status: TaskStatus;
  priority: string;
  due_at: string;
  tags: string;
};

const EMPTY_FORM: TaskForm = {
  title: "",
  description: "",
  status: "todo",
  priority: "normal",
  due_at: "",
  tags: "",
};

const DRAG_MIME = "application/x-keprix-task";

function priorityColor(priority: string): "default" | "info" | "warning" | "error" {
  if (priority === "urgent") return "error";
  if (priority === "high") return "warning";
  if (priority === "low") return "info";
  return "default";
}

function formatDue(dueAt?: string | null): string | null {
  if (!dueAt) return null;
  const date = new Date(dueAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toLocalInputValue(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseTags(raw: string): string[] {
  return raw
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function isOverdue(task: WorkspaceTask): boolean {
  if (!task.due_at || task.status === "done") return false;
  const due = new Date(task.due_at).getTime();
  return Number.isFinite(due) && due < Date.now();
}

function asStatus(value: string | undefined): TaskStatus {
  return COLUMNS.some((column) => column.value === value) ? (value as TaskStatus) : "todo";
}

function emptyBoard(): BoardState {
  return { todo: [], in_progress: [], done: [] };
}

function boardFromTasks(tasks: WorkspaceTask[]): BoardState {
  const board = emptyBoard();
  const sorted = [...tasks].sort((a, b) => {
    const order = (a.sort_order ?? 0) - (b.sort_order ?? 0);
    if (order !== 0) return order;
    return String(a.id).localeCompare(String(b.id));
  });
  for (const task of sorted) {
    board[asStatus(task.status)].push(task);
  }
  return board;
}

function flattenBoard(board: BoardState): WorkspaceTask[] {
  return COLUMNS.flatMap((column) => board[column.value]);
}

function moveOnBoard(
  board: BoardState,
  taskId: string,
  toStatus: TaskStatus,
  toIndex: number,
): BoardState | null {
  const next: BoardState = {
    todo: [...board.todo],
    in_progress: [...board.in_progress],
    done: [...board.done],
  };
  let moving: WorkspaceTask | null = null;
  let fromStatus: TaskStatus | null = null;
  for (const column of COLUMNS) {
    const idx = next[column.value].findIndex((task) => task.id === taskId);
    if (idx >= 0) {
      moving = next[column.value][idx];
      fromStatus = column.value;
      next[column.value].splice(idx, 1);
      break;
    }
  }
  if (!moving || !fromStatus) return null;

  let insertAt = toIndex;
  if (fromStatus === toStatus) {
    const currentIndex = board[fromStatus].findIndex((task) => task.id === taskId);
    if (currentIndex >= 0 && currentIndex < toIndex) insertAt = Math.max(0, toIndex - 1);
  }
  insertAt = Math.max(0, Math.min(insertAt, next[toStatus].length));
  next[toStatus].splice(insertAt, 0, { ...moving, status: toStatus });
  return next;
}

export default function TasksPage() {
  const { data, error, isLoading, mutate } = useSWR("workspace-tasks", () => fetchTasks(), {
    revalidateOnFocus: true,
  });
  const [query, setQuery] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<WorkspaceTask | null>(null);
  const [form, setForm] = React.useState<TaskForm>(EMPTY_FORM);
  const [saving, setSaving] = React.useState(false);
  const [board, setBoard] = React.useState<BoardState>(emptyBoard());
  const [draggingId, setDraggingId] = React.useState<string | null>(null);
  const [dropTarget, setDropTarget] = React.useState<{ status: TaskStatus; index: number } | null>(null);
  const persistLock = React.useRef(false);

  React.useEffect(() => {
    if (persistLock.current) return;
    setBoard(boardFromTasks(data ?? []));
  }, [data]);

  const filteredBoard = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return board;
    const match = (task: WorkspaceTask) =>
      `${task.title} ${task.description} ${(task.tags || []).join(" ")}`.toLowerCase().includes(q);
    return {
      todo: board.todo.filter(match),
      in_progress: board.in_progress.filter(match),
      done: board.done.filter(match),
    };
  }, [board, query]);

  const counts = {
    todo: board.todo.length,
    in_progress: board.in_progress.length,
    done: board.done.length,
    overdue: flattenBoard(board).filter(isOverdue).length,
  };
  const searchActive = Boolean(query.trim());

  function openCreate(status: TaskStatus = "todo") {
    setEditing(null);
    setForm({ ...EMPTY_FORM, status });
    setDialogOpen(true);
  }

  function openEdit(task: WorkspaceTask) {
    setEditing(task);
    setForm({
      title: task.title,
      description: task.description || "",
      status: asStatus(task.status),
      priority: task.priority || "normal",
      due_at: toLocalInputValue(task.due_at),
      tags: (task.tags || []).join(", "),
    });
    setDialogOpen(true);
  }

  async function persistBoard(next: BoardState, movedId: string, previousStatus: TaskStatus) {
    const flat = flattenBoard(next);
    const moved = flat.find((task) => task.id === movedId);
    if (!moved) return;
    persistLock.current = true;
    setBoard(next);
    setMessage(null);
    try {
      if (moved.status !== previousStatus) {
        await updateTask(movedId, { status: moved.status });
      }
      const items = await reorderTasks(flat.map((task) => task.id));
      await mutate(items, { revalidate: false });
      setBoard(boardFromTasks(items));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to move task");
      await mutate();
    } finally {
      persistLock.current = false;
    }
  }

  async function applyMove(taskId: string, toStatus: TaskStatus, toIndex: number) {
    if (searchActive) {
      setMessage("Clear search to drag and reorder the board.");
      return;
    }
    const current = flattenBoard(board).find((task) => task.id === taskId);
    if (!current) return;
    const previousStatus = asStatus(current.status);
    const next = moveOnBoard(board, taskId, toStatus, toIndex);
    if (!next) return;
    const sameSpot =
      previousStatus === toStatus &&
      board[previousStatus].findIndex((task) => task.id === taskId) ===
        next[toStatus].findIndex((task) => task.id === taskId);
    if (sameSpot) return;
    await persistBoard(next, taskId, previousStatus);
  }

  async function handleSave() {
    if (!form.title.trim()) return;
    setSaving(true);
    setMessage(null);
    const payload = {
      title: form.title.trim(),
      description: form.description,
      status: form.status,
      priority: form.priority,
      due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
      tags: parseTags(form.tags),
    };
    try {
      if (editing) await updateTask(editing.id, payload);
      else await createTask(payload);
      setDialogOpen(false);
      setEditing(null);
      setForm(EMPTY_FORM);
      await mutate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to save task");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(task: WorkspaceTask) {
    setMessage(null);
    try {
      await deleteTask(task.id);
      if (editing?.id === task.id) {
        setDialogOpen(false);
        setEditing(null);
      }
      await mutate();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to delete task");
    }
  }

  function onCardDragStart(event: React.DragEvent, task: WorkspaceTask) {
    if (searchActive) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.setData(DRAG_MIME, task.id);
    event.dataTransfer.setData("text/plain", task.id);
    event.dataTransfer.effectAllowed = "move";
    setDraggingId(task.id);
  }

  function onCardDragEnd() {
    setDraggingId(null);
    setDropTarget(null);
  }

  function onColumnDragOver(event: React.DragEvent, status: TaskStatus, index: number) {
    if (searchActive) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setDropTarget({ status, index });
  }

  async function onColumnDrop(event: React.DragEvent, status: TaskStatus, index: number) {
    event.preventDefault();
    const taskId = event.dataTransfer.getData(DRAG_MIME) || event.dataTransfer.getData("text/plain");
    setDraggingId(null);
    setDropTarget(null);
    if (!taskId) return;
    await applyMove(taskId, status, index);
  }

  return (
    <Box>
      <PageHeader
        title="Tasks"
        description="Kanban board: drag cards between columns or reorder within a column. Soft WIP limit on In progress."
        breadcrumbs={[
          { label: "Workspace", href: "/home" },
          { label: "Tasks", href: "/tasks" },
        ]}
        actions={
          <Button variant="contained" onClick={() => openCreate("todo")}>
            New task
          </Button>
        }
      />

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2 }} alignItems={{ sm: "center" }}>
        <TextField
          size="small"
          placeholder="Search title, description, tags..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ flex: 1, minWidth: 220 }}
        />
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip size="small" label={`${counts.todo} to do`} />
          <Chip size="small" color="primary" variant="outlined" label={`${counts.in_progress} in progress`} />
          <Chip size="small" color="success" variant="outlined" label={`${counts.done} done`} />
          {counts.overdue > 0 ? <Chip size="small" color="error" label={`${counts.overdue} overdue`} /> : null}
        </Stack>
      </Stack>

      {message ? (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error instanceof Error ? error.message : "Failed to load tasks"}
        </Alert>
      ) : null}
      {searchActive ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          Search is on; clear it to drag and reorder.
        </Alert>
      ) : null}

      {isLoading ? (
        <SkeletonList rows={8} />
      ) : flattenBoard(board).length === 0 ? (
        <EmptyState
          title="No tasks yet"
          description="Create a task, then drag it across To do, In progress, and Done."
          icon={<TaskAltIcon sx={{ fontSize: 48 }} />}
          actionLabel="New task"
          onAction={() => openCreate("todo")}
        />
      ) : (
        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
            alignItems: "start",
          }}
        >
          {COLUMNS.map((column) => {
            const items = filteredBoard[column.value];
            const wipOver =
              column.wipLimit != null && board[column.value].length > column.wipLimit;
            return (
              <Box
                key={column.value}
                sx={{
                  border: 1,
                  borderColor: dropTarget?.status === column.value ? "primary.main" : "divider",
                  borderRadius: 1,
                  bgcolor: "background.paper",
                  minHeight: 320,
                  display: "flex",
                  flexDirection: "column",
                  transition: "border-color 120ms ease",
                }}
                onDragOver={(e) => onColumnDragOver(e, column.value, items.length)}
                onDrop={(e) => void onColumnDrop(e, column.value, items.length)}
              >
                <Box
                  sx={{
                    px: 1.5,
                    py: 1.25,
                    borderBottom: 1,
                    borderColor: "divider",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 1,
                  }}
                >
                  <Box>
                    <Typography variant="subtitle2" fontWeight={700}>
                      {column.label}
                    </Typography>
                    {column.wipLimit != null ? (
                      <Typography variant="caption" color={wipOver ? "error.main" : "text.secondary"}>
                        WIP {board[column.value].length}/{column.wipLimit}
                        {wipOver ? " (over)" : ""}
                      </Typography>
                    ) : null}
                  </Box>
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <Chip size="small" color={wipOver ? "error" : "default"} label={items.length} />
                    {column.value !== "done" ? (
                      <Button size="small" onClick={() => openCreate(column.value)}>
                        Add
                      </Button>
                    ) : null}
                  </Stack>
                </Box>
                <Stack spacing={1} sx={{ p: 1.25, flex: 1 }}>
                  {items.length === 0 ? (
                    <Box
                      sx={{
                        border: "1px dashed",
                        borderColor: "divider",
                        borderRadius: 1,
                        px: 1,
                        py: 2,
                        textAlign: "center",
                      }}
                      onDragOver={(e) => onColumnDragOver(e, column.value, 0)}
                      onDrop={(e) => void onColumnDrop(e, column.value, 0)}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {searchActive ? "No matches" : "Drop tasks here"}
                      </Typography>
                    </Box>
                  ) : (
                    items.map((task, index) => {
                      const showGap =
                        dropTarget?.status === column.value && dropTarget.index === index && draggingId !== task.id;
                      return (
                        <React.Fragment key={task.id}>
                          {showGap ? (
                            <Box
                              sx={{
                                height: 6,
                                borderRadius: 1,
                                bgcolor: "primary.main",
                                opacity: 0.7,
                              }}
                            />
                          ) : null}
                          <Box
                            draggable={!searchActive}
                            onDragStart={(e) => onCardDragStart(e, task)}
                            onDragEnd={onCardDragEnd}
                            onDragOver={(e) => onColumnDragOver(e, column.value, index)}
                            onDrop={(e) => void onColumnDrop(e, column.value, index)}
                            sx={{
                              border: 1,
                              borderColor: isOverdue(task) ? "error.light" : "divider",
                              borderRadius: 1,
                              p: 1.25,
                              bgcolor: "background.default",
                              cursor: searchActive ? "pointer" : "grab",
                              opacity: draggingId === task.id ? 0.45 : 1,
                              "&:active": { cursor: searchActive ? "pointer" : "grabbing" },
                              "&:hover": { borderColor: "primary.light" },
                            }}
                            onClick={() => openEdit(task)}
                          >
                            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.5 }}>
                              <DragIndicatorIcon
                                fontSize="small"
                                sx={{ color: "text.disabled", mt: 0.25, flexShrink: 0 }}
                              />
                              <Typography variant="body2" fontWeight={600} sx={{ flex: 1 }}>
                                {task.title}
                              </Typography>
                              <IconButton
                                size="small"
                                aria-label="Delete task"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  void handleDelete(task);
                                }}
                              >
                                <DeleteOutlineIcon fontSize="small" />
                              </IconButton>
                            </Box>
                            {task.description ? (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{
                                  display: "-webkit-box",
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: "vertical",
                                  overflow: "hidden",
                                  mt: 0.5,
                                  pl: 3,
                                }}
                              >
                                {task.description}
                              </Typography>
                            ) : null}
                            <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ mt: 1, pl: 3 }}>
                              <Chip size="small" label={task.priority} color={priorityColor(task.priority)} />
                              {task.agent_scheduled ? (
                                <Chip
                                  size="small"
                                  icon={<SmartToyIcon />}
                                  label="Agent"
                                  color="info"
                                  variant="outlined"
                                />
                              ) : null}
                              {formatDue(task.due_at) ? (
                                <Chip
                                  size="small"
                                  variant="outlined"
                                  color={isOverdue(task) ? "error" : "default"}
                                  label={
                                    isOverdue(task)
                                      ? `Overdue ${formatDue(task.due_at)}`
                                      : `Due ${formatDue(task.due_at)}`
                                  }
                                />
                              ) : null}
                              {(task.tags || []).slice(0, 3).map((tag) => (
                                <Chip key={tag} size="small" variant="outlined" label={tag} />
                              ))}
                            </Stack>
                            <Stack
                              direction="row"
                              spacing={0.5}
                              sx={{ mt: 1, pl: 3 }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {column.value === "todo" ? (
                                <Button
                                  size="small"
                                  onClick={() => void applyMove(task.id, "in_progress", board.in_progress.length)}
                                >
                                  Start
                                </Button>
                              ) : null}
                              {column.value !== "done" ? (
                                <Button
                                  size="small"
                                  onClick={() => void applyMove(task.id, "done", board.done.length)}
                                >
                                  Complete
                                </Button>
                              ) : (
                                <Button
                                  size="small"
                                  onClick={() => void applyMove(task.id, "todo", board.todo.length)}
                                >
                                  Reopen
                                </Button>
                              )}
                            </Stack>
                          </Box>
                        </React.Fragment>
                      );
                    })
                  )}
                  {dropTarget?.status === column.value && dropTarget.index === items.length && items.length > 0 ? (
                    <Box sx={{ height: 6, borderRadius: 1, bgcolor: "primary.main", opacity: 0.7 }} />
                  ) : null}
                </Stack>
              </Box>
            );
          })}
        </Box>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? "Edit task" : "New task"}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="Title"
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
            autoFocus
          />
          <TextField
            label="Description"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
            multiline
            minRows={3}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              select
              label="Status"
              value={form.status}
              onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value as TaskStatus }))}
              fullWidth
            >
              {COLUMNS.map((column) => (
                <MenuItem key={column.value} value={column.value}>
                  {column.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Priority"
              value={form.priority}
              onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value }))}
              fullWidth
            >
              {PRIORITIES.map((priority) => (
                <MenuItem key={priority} value={priority}>
                  {priority}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          <TextField
            label="Due"
            type="datetime-local"
            value={form.due_at}
            onChange={(e) => setForm((prev) => ({ ...prev, due_at: e.target.value }))}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="Tags"
            value={form.tags}
            onChange={(e) => setForm((prev) => ({ ...prev, tags: e.target.value }))}
            helperText="Comma-separated"
          />
        </DialogContent>
        <DialogActions>
          {editing ? (
            <Button color="error" onClick={() => void handleDelete(editing)} sx={{ mr: "auto" }}>
              Delete
            </Button>
          ) : null}
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving || !form.title.trim()}>
            {editing ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

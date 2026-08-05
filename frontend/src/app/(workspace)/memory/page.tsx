"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import MemoryIcon from "@mui/icons-material/Memory";
import NextLink from "next/link";
import * as React from "react";
import BrainSectionTabs from "@/components/memory/BrainSectionTabs";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";
import { formatTimeAgo } from "@/lib/time-ago";

type MemoryRow = {
  id: string;
  content: string;
  tags?: string[];
  created_at?: string;
  score?: number;
  metadata?: Record<string, unknown>;
};

type Overview = {
  memories: MemoryRow[];
  types: string[];
  continuity: {
    score: number;
    completeness: number;
    staleness: number;
    contradiction_rate: number;
    counts: Record<string, unknown>;
  };
  constitution: {
    title: string;
    rules: string[];
    gates: Record<string, boolean>;
  };
  graph: { entities: Array<Record<string, unknown>>; relations: Array<Record<string, unknown>> };
  conflicts: Array<{
    id: string;
    left_memory_id: string;
    right_memory_id: string;
    left_content: string;
    right_content: string;
  }>;
  count: number;
};

async function loadOverview(): Promise<Overview> {
  const response = await ceApi("/api/memory/hub/overview");
  if (!response.ok) throw new Error("Failed to load memory hub");
  return response.json();
}

export default function MemoryPage() {
  const [tab, setTab] = React.useState(0);
  const [overview, setOverview] = React.useState<Overview | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [recall, setRecall] = React.useState<Record<string, unknown> | null>(null);
  const [draftContent, setDraftContent] = React.useState("");
  const [draftTags, setDraftTags] = React.useState("");
  const [draftType, setDraftType] = React.useState("preference");
  const [draftSide, setDraftSide] = React.useState("user");
  const [editing, setEditing] = React.useState<MemoryRow | null>(null);
  const [editContent, setEditContent] = React.useState("");
  const [editTags, setEditTags] = React.useState("");
  const [filterType, setFilterType] = React.useState("all");

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await ceApi("/api/memory/hub/bootstrap", { method: "POST" }).catch(() => undefined);
      setOverview(await loadOverview());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memory");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const rows = React.useMemo(() => {
    const list = overview?.memories || [];
    if (filterType === "all") return list;
    return list.filter((row) => String(row.metadata?.memory_type || "episodic") === filterType);
  }, [filterType, overview]);

  const runRecall = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi("/api/memory/hub/recall", {
        method: "POST",
        body: JSON.stringify({ query, limit: 12, include_self: draftSide === "self" }),
      });
      if (!response.ok) throw new Error("Recall failed");
      setRecall(await response.json());
      setTab(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recall failed");
    } finally {
      setBusy(false);
    }
  };

  const onAdd = async () => {
    if (!draftContent.trim()) {
      setError("Enter memory content");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi("/api/memory/hub/save", {
        method: "POST",
        body: JSON.stringify({
          content: draftContent.trim(),
          tags: draftTags.split(",").map((p) => p.trim()).filter(Boolean),
          memory_type: draftType,
          model_side: draftSide,
          pin: false,
          source: "manual",
        }),
      });
      if (!response.ok) throw new Error("Save failed");
      setDraftContent("");
      setDraftTags("");
      setStatus("Memory saved");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onSaveEdit = async () => {
    if (!editing) return;
    setBusy(true);
    try {
      const response = await ceApi(`/api/memory/hub/${editing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          content: editContent.trim(),
          tags: editTags.split(",").map((p) => p.trim()).filter(Boolean),
        }),
      });
      if (!response.ok) throw new Error("Update failed");
      setEditing(null);
      setStatus("Updated");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (id: string) => {
    setBusy(true);
    try {
      const response = await ceApi(`/api/memory/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Delete failed");
      setStatus("Deleted");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  const resolveConflict = async (winnerId: string, loserId: string) => {
    setBusy(true);
    try {
      const response = await ceApi("/api/memory/hub/conflicts/resolve", {
        method: "POST",
        body: JSON.stringify({ winner_id: winnerId, loser_id: loserId }),
      });
      if (!response.ok) throw new Error("Resolve failed");
      setStatus("Conflict resolved");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolve failed");
    } finally {
      setBusy(false);
    }
  };

  const runDream = async () => {
    setBusy(true);
    try {
      const response = await ceApi("/api/memory/hub/dream", { method: "POST" });
      if (!response.ok) throw new Error("Dream run failed");
      const detail = await response.json();
      setStatus(`Dream done: promoted ${detail.promoted}, archived ${detail.archived}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dream failed");
    } finally {
      setBusy(false);
    }
  };

  const exportMemories = async () => {
    const response = await ceApi("/api/memory/hub/export");
    if (!response.ok) {
      setError("Export failed");
      return;
    }
    const payload = await response.json();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "keprix-memory-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setStatus("Exported");
  };

  const continuity = overview?.continuity;
  const constitution = overview?.constitution;

  return (
    <Box>
      <PageHeader
        title="Brain"
        description="Typed facts, recall, Temporal graph, belief revision, and dreaming."
        actions={
          <>
            <Button component={NextLink} href="/brain/graphiti" variant="outlined" size="small" sx={{ textTransform: "none" }}>
              Graphiti
            </Button>
            <Button variant="outlined" size="small" onClick={() => void exportMemories()} sx={{ textTransform: "none" }}>
              Export
            </Button>
            <Button variant="contained" size="small" disableElevation disabled={busy} onClick={() => void runDream()} sx={{ textTransform: "none" }}>
              Run dream
            </Button>
          </>
        }
      />
      <BrainSectionTabs value="list" />

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {status && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setStatus(null)}>{status}</Alert>}

      {continuity && (
        <Box sx={{ mb: 2, p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2">Continuity score {Math.round(continuity.score * 100)}</Typography>
              <LinearProgress variant="determinate" value={Math.round(continuity.score * 100)} sx={{ mt: 1, mb: 1 }} />
              <Typography variant="caption" color="text.secondary">
                completeness {Math.round(continuity.completeness * 100)} · staleness {Math.round(continuity.staleness * 100)} · contradiction {Math.round(continuity.contradiction_rate * 100)}
              </Typography>
            </Box>
            <Chip label={`${overview?.count || 0} memories`} />
            <Chip label={`${overview?.graph?.entities?.length || 0} entities`} />
            <Chip label={`${overview?.conflicts?.length || 0} conflicts`} color={overview?.conflicts?.length ? "warning" : "default"} />
          </Stack>
        </Box>
      )}

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 2 }}>
        <TextField size="small" fullWidth label="Unified recall query" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void runRecall()} />
        <Button variant="contained" disabled={busy} onClick={() => void runRecall()}>Recall</Button>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} sx={{ mb: 2 }}>
        <TextField size="small" fullWidth label="Add durable memory" value={draftContent} onChange={(e) => setDraftContent(e.target.value)} />
        <TextField size="small" label="Tags" value={draftTags} onChange={(e) => setDraftTags(e.target.value)} sx={{ minWidth: 160 }} />
        <TextField select size="small" label="Type" value={draftType} onChange={(e) => setDraftType(e.target.value)} sx={{ minWidth: 140 }}>
          {(overview?.types || ["preference", "profile", "decision", "semantic", "entity", "open_loop", "episodic", "self"]).map((t) => (
            <MenuItem key={t} value={t}>{t}</MenuItem>
          ))}
        </TextField>
        <TextField select size="small" label="Side" value={draftSide} onChange={(e) => setDraftSide(e.target.value)} sx={{ minWidth: 110 }}>
          <MenuItem value="user">user</MenuItem>
          <MenuItem value="self">self</MenuItem>
        </TextField>
        <Button variant="contained" disabled={busy} onClick={() => void onAdd()}>Add</Button>
      </Stack>

      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Memories" />
        <Tab label="Recall debug" />
        <Tab label="Temporal graph" />
        <Tab label="Conflicts" />
        <Tab label="Constitution" />
      </Tabs>

      {loading ? (
        <SkeletonTable rows={6} columns={4} />
      ) : tab === 0 ? (
        <>
          <Stack direction="row" spacing={1} sx={{ mb: 1 }} useFlexGap flexWrap="wrap">
            <Chip label="all" color={filterType === "all" ? "primary" : "default"} onClick={() => setFilterType("all")} />
            {(overview?.types || []).map((t) => (
              <Chip key={t} label={t} color={filterType === t ? "primary" : "default"} onClick={() => setFilterType(t)} />
            ))}
          </Stack>
          {rows.length === 0 ? (
            <EmptyState title="No memory entries" description="Add facts above, chat with REM on, ingest OCR, or run dream." icon={<MemoryIcon sx={{ fontSize: 48 }} />} />
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Content</TableCell>
                  <TableCell>Type / belief</TableCell>
                  <TableCell>Tags</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ maxWidth: 480 }}>
                      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{row.content}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {String(row.metadata?.source || "manual")} · {String(row.metadata?.modality || "text")} · side {String(row.metadata?.model_side || "user")}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={String(row.metadata?.memory_type || "episodic")} sx={{ mr: 0.5 }} />
                      <Chip size="small" label={String(row.metadata?.belief_state || "active")} />
                    </TableCell>
                    <TableCell>{(row.tags || []).map((tag) => <Chip key={tag} size="small" label={tag} sx={{ mr: 0.5 }} />)}</TableCell>
                    <TableCell><Typography variant="caption">{row.created_at ? formatTimeAgo(row.created_at) : "-"}</Typography></TableCell>
                    <TableCell align="right">
                      <Button size="small" startIcon={<EditOutlinedIcon />} onClick={() => { setEditing(row); setEditContent(row.content); setEditTags((row.tags || []).join(", ")); }}>Edit</Button>
                      <Button size="small" color="error" startIcon={<DeleteOutlineIcon />} onClick={() => void onDelete(row.id)}>Delete</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </>
      ) : tab === 1 ? (
        <Box component="pre" sx={{ p: 2, bgcolor: "action.hover", borderRadius: 1, whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
          {recall ? JSON.stringify(recall, null, 2) : "Run a recall query to inspect budgeted hits and provenance."}
        </Box>
      ) : tab === 2 ? (
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle2">Entities</Typography>
            <Button component={NextLink} href="/brain/graph?kinds=memory,entity,session" size="small" variant="outlined">
              Open unified Brain graph
            </Button>
          </Stack>
          <Table size="small">
            <TableBody>
              {(overview?.graph?.entities || []).map((entity) => (
                <TableRow key={String(entity.id)}>
                  <TableCell>{String(entity.name)}</TableCell>
                  <TableCell>{String(entity.entity_type)}</TableCell>
                  <TableCell>{String(entity.belief_state)}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      component={NextLink}
                      href={`/brain/graph?kind=entity&id=${encodeURIComponent(String(entity.id))}`}
                    >
                      Open in Brain
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Typography variant="subtitle2">Relations</Typography>
          <Table size="small">
            <TableBody>
              {(overview?.graph?.relations || []).map((rel) => (
                <TableRow key={String(rel.id)}>
                  <TableCell>{String(rel.subject_name)} -[{String(rel.predicate)}]-> {String(rel.object_name)}</TableCell>
                  <TableCell>{String(rel.confidence)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Stack>
      ) : tab === 3 ? (
        (overview?.conflicts || []).length === 0 ? (
          <Typography color="text.secondary">No open conflicts detected.</Typography>
        ) : (
          <Stack spacing={2}>
            {(overview?.conflicts || []).map((conflict) => (
              <Box key={conflict.id} sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Typography variant="body2" sx={{ mb: 1 }}>A: {conflict.left_content}</Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>B: {conflict.right_content}</Typography>
                <Stack direction="row" spacing={1}>
                  <Button size="small" variant="contained" onClick={() => void resolveConflict(conflict.left_memory_id, conflict.right_memory_id)}>Keep A</Button>
                  <Button size="small" variant="outlined" onClick={() => void resolveConflict(conflict.right_memory_id, conflict.left_memory_id)}>Keep B</Button>
                </Stack>
              </Box>
            ))}
          </Stack>
        )
      ) : (
        <Box>
          <Typography variant="h6" gutterBottom>{constitution?.title || "Memory Constitution"}</Typography>
          <Stack component="ul" sx={{ pl: 2 }}>
            {(constitution?.rules || []).map((rule) => (
              <Typography component="li" key={rule} variant="body2" sx={{ mb: 1 }}>{rule}</Typography>
            ))}
          </Stack>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {Object.entries(constitution?.gates || {}).map(([key, value]) => (
              <Chip key={key} label={`${key}: ${value ? "on" : "off"}`} color={value ? "success" : "default"} />
            ))}
          </Stack>
        </Box>
      )}

      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} fullWidth maxWidth="sm">
        <DialogTitle>Edit memory</DialogTitle>
        <DialogContent>
          <Stack spacing={1.5} sx={{ pt: 1 }}>
            <TextField label="Content" multiline minRows={4} value={editContent} onChange={(e) => setEditContent(e.target.value)} fullWidth />
            <TextField label="Tags" value={editTags} onChange={(e) => setEditTags(e.target.value)} fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={() => void onSaveEdit()}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

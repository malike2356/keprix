"use client";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ConnectionsList from "@/components/brain/ConnectionsList";
import { SkeletonBlock } from "@/components/ui/loading";
import { PanelEditForm } from "@/components/brain/panel-edit/panel-edit-registry";
import { renderPanelContent } from "@/components/brain/panel-content/panel-registry";
import { ceApi } from "@/lib/ce-api";
import { fetchSharedBrainNode } from "@/lib/brain-share-api";
import type { BrainGraphData, GraphNode } from "@/types/brain-graph";

type Props = {
  node: GraphNode | null;
  onClose: () => void;
  onNavigateTo?: (kind: string, id: string) => void;
  readOnly?: boolean;
  shareContext?: { shareId: string; password?: string | null };
  graphData?: BrainGraphData | null;
};

function fullPageHref(node: GraphNode): string {
  if (node.kind === "session") {
    if (node.id === "memory-hub") return "/memory";
    return `/chat?session=${encodeURIComponent(node.id)}`;
  }
  if (node.kind === "task") return `/tasks`;
  if (node.kind === "document") return `/documents`;
  if (node.kind === "skill") return `/skills`;
  if (node.kind === "source") return `/research`;
  if (node.kind === "entity") return `/memory?tab=graph&kind=entity&id=${encodeURIComponent(node.id)}`;
  if (node.kind === "memory") return `/memory?kind=memory&id=${encodeURIComponent(node.id)}`;
  return `/memory`;
}

function editEndpoint(node: GraphNode): string | null {
  if (node.kind === "memory") return `/api/memory/hub/${encodeURIComponent(node.id)}`;
  if (node.kind === "skill") return `/api/skills/${encodeURIComponent(node.id)}`;
  if (node.kind === "task") return `/api/tasks/${encodeURIComponent(node.id)}`;
  return null;
}

export default function NodeContentPanel({ node, onClose, onNavigateTo, readOnly = false, shareContext, graphData }: Props) {
  const [active, setActive] = React.useState<GraphNode | null>(node);
  const [full, setFull] = React.useState<GraphNode | null>(node);
  const [loading, setLoading] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [history, setHistory] = React.useState<GraphNode[]>(node ? [node] : []);
  const [index, setIndex] = React.useState(node ? 0 : -1);

  const [editError, setEditError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!node) return;
    setActive(node);
    setHistory([node]);
    setIndex(0);
    setEditing(false);
    setEditError(null);
  }, [node]);

  React.useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setLoading(true);
    const load = shareContext
      ? fetchSharedBrainNode(shareContext.shareId, active.kind, active.id, shareContext.password)
      : ceApi(`/api/brain/graph/node/${encodeURIComponent(active.kind)}/${encodeURIComponent(active.id)}`).then(async (response) => {
          if (!response.ok) throw new Error("Failed to load node");
          return (await response.json()) as GraphNode;
        });
    void load
      .then((payload) => {
        if (!cancelled) setFull(payload as GraphNode);
      })
      .catch(() => {
        if (!cancelled) setFull(active);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active, shareContext]);

  const navigate = (next: GraphNode) => {
    setActive(next);
    setFull(next);
    setEditing(false);
    setEditError(null);
    setHistory((items) => [...items.slice(0, index + 1), next]);
    setIndex((value) => value + 1);
    onNavigateTo?.(next.kind, next.id);
  };

  const go = (direction: -1 | 1) => {
    const nextIndex = index + direction;
    const next = history[nextIndex];
    if (!next) return;
    setIndex(nextIndex);
    setActive(next);
    setFull(next);
    setEditing(false);
    setEditError(null);
    onNavigateTo?.(next.kind, next.id);
  };

  const save = async (body: Record<string, unknown>) => {
    if (!full) return;
    setEditError(null);
    const endpoint = editEndpoint(full);
    if (endpoint) {
      const response = await ceApi(endpoint, { method: "PATCH", body: JSON.stringify(body) }).catch(() => null);
      if (!response || !response.ok) {
        const detail = response ? await response.text().catch(() => "") : "";
        setEditError(detail || "Could not save changes. Try again from the Memory hub.");
        return;
      }
    }
    const updated = { ...full, label: String(body.title || body.name || full.label), summary: String(body.content || body.description || body.body || full.summary) };
    setFull(updated);
    setActive(updated);
    setEditing(false);
  };

  const remove = async () => {
    if (!full) return;
    const ok = window.confirm(`Delete this ${full.kind}? Connections will also be removed.`);
    if (!ok) return;
    const endpoint = editEndpoint(full);
    if (endpoint) {
      await ceApi(endpoint, { method: "DELETE" }).catch(() => undefined);
    }
    await ceApi(`/api/brain/graph/edges?source_kind=${encodeURIComponent(full.kind)}&source_id=${encodeURIComponent(full.id)}`, { method: "DELETE" }).catch(() => undefined);
    setFull({ ...full, deleted: true, label: "[deleted]" });
  };

  if (!active || !full) return null;
  const panelReadOnly = readOnly || full.kind === "tool" || full.kind === "entity" || full.deleted || full.id === "memory-hub";
  return (
    <Paper
      square
      variant="outlined"
      sx={{
        borderTop: 0,
        borderRight: 0,
        borderBottom: 0,
        width: { xs: "100%", md: 320 },
        position: { xs: "fixed", md: "relative" },
        inset: { xs: 0, md: "auto" },
        zIndex: { xs: 1300, md: "auto" },
        display: "grid",
        gridTemplateRows: "auto 1fr auto",
        bgcolor: "background.paper",
      }}
    >
      <Stack direction="row" alignItems="center" spacing={0.5} sx={{ p: 1.5, borderBottom: 1, borderColor: "divider" }}>
        <IconButton size="small" disabled={index <= 0} onClick={() => go(-1)} aria-label="Back">
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <IconButton size="small" disabled={index >= history.length - 1} onClick={() => go(1)} aria-label="Forward">
          <ArrowForwardIcon fontSize="small" />
        </IconButton>
        <Chip size="small" label={full.kind} />
        <Typography variant="subtitle2" sx={{ flex: 1 }} noWrap>
          {full.deleted ? "[deleted]" : full.label}
        </Typography>
        <IconButton size="small" onClick={onClose} aria-label="Close node panel">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Box sx={{ p: 2, overflow: "auto" }}>
        {loading ? (
          <Stack spacing={1}>
            <SkeletonBlock height={28} />
            <SkeletonBlock height={140} />
          </Stack>
        ) : editing ? (
          <PanelEditForm node={full} onSave={save} onCancel={() => setEditing(false)} />
        ) : (
          renderPanelContent(full)
        )}
        {editError ? (
          <Typography variant="caption" color="error" sx={{ display: "block", mt: 1 }}>
            {editError}
          </Typography>
        ) : null}
        <Divider sx={{ my: 2 }} />
        <ConnectionsList kind={full.kind} id={full.id} onNavigateTo={navigate} graphData={graphData} />
      </Box>
      {!panelReadOnly ? (
        <Stack direction="row" spacing={1} sx={{ p: 1.5, borderTop: 1, borderColor: "divider", flexWrap: "wrap" }}>
          <Button size="small" startIcon={<EditIcon />} onClick={() => setEditing(true)}>Edit</Button>
          <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => void remove()}>Delete</Button>
          <Button size="small" href={fullPageHref(full)} startIcon={<OpenInNewIcon />}>Open</Button>
        </Stack>
      ) : null}
    </Paper>
  );
}

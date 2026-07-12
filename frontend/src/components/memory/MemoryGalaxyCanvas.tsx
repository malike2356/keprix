"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import ErrorState from "@/components/ui/ErrorState";
import { applyLayout } from "@/lib/brain/layout-registry";
import type { BrainFlowNodeData } from "@/types/brain-graph";
import { ceApi } from "@/lib/ce-api";

export type VaultGraphPayload = {
  nodes: Array<{ id: string; label: string }>;
  edges: Array<{ source: string; target: string }>;
};

export type GalaxyLayoutMode = "circle" | "force";

function circlePositions(nodes: VaultGraphPayload["nodes"]): Record<string, { x: number; y: number }> {
  const count = Math.max(nodes.length, 1);
  const radius = Math.min(280, 40 + count * 12);
  const positions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / count;
    positions[node.id] = {
      x: 360 + radius * Math.cos(angle),
      y: 280 + radius * Math.sin(angle),
    };
  });
  return positions;
}

function toFlowNodes(
  nodes: VaultGraphPayload["nodes"],
  positions: Record<string, { x: number; y: number }>,
): Node[] {
  return nodes.map((node) => ({
    id: node.id,
    data: { label: node.label || node.id, path: node.id },
    position: positions[node.id] ?? { x: 0, y: 0 },
    style: {
      borderRadius: 12,
      border: "1px solid var(--mui-palette-divider, #ccc)",
      padding: "6px 10px",
      fontSize: 12,
      background: "var(--mui-palette-background-paper, #fff)",
      maxWidth: 180,
      cursor: "pointer",
    },
  }));
}

function toEdges(edges: VaultGraphPayload["edges"]): Edge[] {
  return edges.map((edge, index) => ({
    id: `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { strokeWidth: 1.2 },
  }));
}

function toLayoutInput(nodes: VaultGraphPayload["nodes"], edges: VaultGraphPayload["edges"]) {
  const circle = circlePositions(nodes);
  const flowNodes: Node<BrainFlowNodeData>[] = nodes.map((node) => ({
    id: node.id,
    position: circle[node.id] ?? { x: 0, y: 0 },
    data: {
      id: node.id,
      kind: "document",
      label: node.label || node.id,
      summary: "",
      created_at: "",
      metadata: { path: node.id },
      deleted: false,
      degree: 1,
      size: 44,
    },
  }));
  return { nodes: flowNodes, edges: toEdges(edges) };
}

type Props = {
  graph?: VaultGraphPayload;
  loading?: boolean;
  layoutMode?: GalaxyLayoutMode;
  onLayoutModeChange?: (mode: GalaxyLayoutMode) => void;
};

function GalaxyInner({ graph, loading, layoutMode = "circle", onLayoutModeChange }: Props) {
  const { fitView } = useReactFlow();
  const [nodes, setNodes] = React.useState<Node[]>([]);
  const [edges, setEdges] = React.useState<Edge[]>([]);
  const [layoutBusy, setLayoutBusy] = React.useState(false);
  const [selectedPath, setSelectedPath] = React.useState<string | null>(null);
  const [noteContent, setNoteContent] = React.useState<string | null>(null);
  const [noteError, setNoteError] = React.useState<string | null>(null);
  const [noteLoading, setNoteLoading] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    const payload = graph ?? { nodes: [], edges: [] };
    const nextEdges = toEdges(payload.edges);

    async function run() {
      if (!payload.nodes.length) {
        if (!cancelled) {
          setNodes([]);
          setEdges([]);
        }
        return;
      }
      setLayoutBusy(true);
      try {
        let positions: Record<string, { x: number; y: number }>;
        if (layoutMode === "force") {
          positions = await applyLayout("force", toLayoutInput(payload.nodes, payload.edges));
        } else {
          positions = circlePositions(payload.nodes);
        }
        if (cancelled) return;
        setNodes(toFlowNodes(payload.nodes, positions));
        setEdges(nextEdges);
        requestAnimationFrame(() => fitView({ padding: 0.2 }));
      } finally {
        if (!cancelled) setLayoutBusy(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [graph, layoutMode, fitView]);

  const openNote = React.useCallback(async (path: string) => {
    setSelectedPath(path);
    setNoteContent(null);
    setNoteError(null);
    setNoteLoading(true);
    try {
      const encoded = path
        .split("/")
        .map((segment) => encodeURIComponent(segment))
        .join("/");
      const response = await ceApi(`/api/vault/files/${encoded}`);
      if (!response.ok) {
        throw new Error((await response.text()) || "Note not found in vault");
      }
      const payload = (await response.json()) as { content?: string; path?: string };
      setNoteContent(payload.content ?? "(empty note)");
    } catch (err) {
      setNoteError(err instanceof Error ? err.message : "Could not open note");
    } finally {
      setNoteLoading(false);
    }
  }, []);

  const onNodeClick: NodeMouseHandler = React.useCallback(
    (_event, node) => {
      void openNote(String(node.id));
    },
    [openNote],
  );

  if (loading || layoutBusy) {
    return (
      <Box sx={{ height: "100%", display: "grid", placeItems: "center" }}>
        <Typography color="text.secondary">
          {layoutBusy ? "Arranging Memory Galaxy…" : "Loading Memory Galaxy…"}
        </Typography>
      </Box>
    );
  }

  if (!nodes.length) {
    return (
      <EmptyState
        title="Your vault is empty"
        description="Connect a markdown vault, then capture notes from chat or Agent OS memory workflows."
        actionLabel="Vault settings"
        onAction={() => {
          window.location.href = "/settings/vault";
        }}
      />
    );
  }

  return (
    <>
      {onLayoutModeChange ? (
        <Stack direction="row" justifyContent="flex-end" sx={{ mb: 1 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={layoutMode}
            onChange={(_event, value: GalaxyLayoutMode | null) => {
              if (value) onLayoutModeChange(value);
            }}
          >
            <ToggleButton value="circle">Circle</ToggleButton>
            <ToggleButton value="force">Force</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
      ) : null}
      <Box sx={{ height: "100%", minHeight: 440 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          onNodeClick={onNodeClick}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={18} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </Box>
      <Drawer
        anchor="right"
        open={Boolean(selectedPath)}
        onClose={() => setSelectedPath(null)}
        PaperProps={{ sx: { width: { xs: "100%", sm: 420 }, p: 2 } }}
      >
        <Typography variant="h6" sx={{ mb: 1 }}>
          {selectedPath || "Note"}
        </Typography>
        {noteLoading ? <Typography color="text.secondary">Loading…</Typography> : null}
        {noteError ? (
          <ErrorState
            title="Could not open note"
            message={noteError}
            onRetry={() => selectedPath && void openNote(selectedPath)}
          />
        ) : null}
        {noteContent ? (
          <Box
            component="pre"
            sx={{
              m: 0,
              whiteSpace: "pre-wrap",
              fontSize: "0.85rem",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            }}
          >
            {noteContent}
          </Box>
        ) : null}
        <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
          <Button component={Link} href="/settings/vault" size="small" variant="outlined">
            Vault settings
          </Button>
          <Button size="small" onClick={() => setSelectedPath(null)}>
            Close
          </Button>
        </Stack>
      </Drawer>
    </>
  );
}

export default function MemoryGalaxyCanvas(props: Props) {
  return (
    <Box sx={{ height: "100%", minHeight: 480, border: 1, borderColor: "divider", borderRadius: 2, overflow: "hidden", p: 1 }}>
      <ReactFlowProvider>
        <GalaxyInner {...props} />
      </ReactFlowProvider>
    </Box>
  );
}

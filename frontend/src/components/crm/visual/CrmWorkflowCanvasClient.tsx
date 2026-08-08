"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import CrmNodeInspector from "@/components/crm/visual/CrmNodeInspector";
import CrmStatusBadge from "@/components/crm/visual/CrmStatusBadge";
import StructuredDataView from "@/components/ui/StructuredDataView";
import { CRM_WORKSPACE } from "@/components/crm/types";
import {
  createCrmVisualRun,
  fetchCrmVisualWorkflow,
  publishCrmVisualWorkflow,
  saveCrmVisualWorkflow,
  simulateCrmVisualWorkflow,
  validateCrmVisualWorkflow,
} from "@/lib/crm-api";

type GraphNode = {
  id: string;
  family?: string;
  type?: string;
  label?: string;
  config?: Record<string, unknown>;
  x?: number;
  y?: number;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  condition_label?: string;
};

type Props = {
  workflowId: string;
};

function OutlineEditor({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <List dense aria-label="Workflow outline">
      {nodes.map((node, idx) => {
        const outs = edges.filter((e) => e.source === node.id);
        return (
          <ListItemButton
            key={node.id}
            selected={selectedId === node.id}
            onClick={() => onSelect(node.id)}
          >
            <ListItemText
              primary={`${idx + 1}. ${node.label || node.type || node.id}`}
              secondary={`${node.family || "node"} · ${outs.map((e) => `${e.condition_label || "next"} -> ${e.target}`).join("; ") || "no outs"}`}
            />
          </ListItemButton>
        );
      })}
    </List>
  );
}

function CanvasInner({
  nodes,
  edges,
  selectedId,
  onSelect,
  onNodeMoved,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onNodeMoved?: (id: string, x: number, y: number) => void;
}) {
  const flowNodes: Node[] = nodes.map((n) => ({
    id: n.id,
    position: { x: n.x ?? 0, y: n.y ?? 0 },
    data: { label: `${n.label || n.type || n.id}\n[${n.family || "node"}]` },
    style: {
      border: selectedId === n.id ? "2px solid #1976d2" : "1px solid #999",
      borderRadius: 8,
      padding: 8,
      background: "#fff",
      fontSize: 12,
      whiteSpace: "pre-line",
      minWidth: 140,
    },
  }));
  const flowEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.condition_label || "",
  }));

  return (
    <Box sx={{ height: 520 }} aria-label="Workflow canvas">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        onNodeClick={(_, n) => onSelect(n.id)}
        onPaneClick={() => onSelect(null)}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        onNodeDragStop={(_event, node) => {
          onSelect(node.id);
          onNodeMoved?.(node.id, node.position.x, node.position.y);
        }}
      >
        <Background gap={20} />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </Box>
  );
}

function CrmWorkflowCanvasInner({ workflowId }: Props) {
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [view, setView] = React.useState<"canvas" | "outline">("canvas");
  const [sim, setSim] = React.useState<Record<string, unknown> | null>(null);

  const data = useSWR(["crm-visual-wf", CRM_WORKSPACE, workflowId], () =>
    fetchCrmVisualWorkflow(workflowId, CRM_WORKSPACE),
  );

  const graph = (data.data?.graph || {}) as {
    id?: string;
    name?: string;
    status?: string;
    workflow_version?: number;
    nodes?: GraphNode[];
    edges?: GraphEdge[];
  };
  const [localNodes, setLocalNodes] = React.useState<GraphNode[]>([]);
  const [paletteFamily, setPaletteFamily] = React.useState("outreach");

  const remoteNodesKey = `${String(graph.id || "")}:${String(graph.workflow_version ?? "")}:${(graph.nodes || []).length}`;
  React.useEffect(() => {
    setLocalNodes(graph.nodes || []);
    // Reset local edits when the server graph identity/version changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by remoteNodesKey
  }, [remoteNodesKey]);

  const nodes = localNodes;
  const edges = graph.edges || [];
  const validation = data.data?.validation;

  const onNodeMoved = (id: string, x: number, y: number) => {
    setLocalNodes((prev) => prev.map((n) => (n.id === id ? { ...n, x, y } : n)));
  };

  const addNode = () => {
    const id = `node-${Date.now().toString(36)}`;
    setLocalNodes((prev) => [
      ...prev,
      {
        id,
        family: paletteFamily,
        type: paletteFamily,
        label: `New ${paletteFamily}`,
        x: 80 + (prev.length % 4) * 180,
        y: 80 + Math.floor(prev.length / 4) * 100,
        config: {},
      },
    ]);
    setSelectedId(id);
    setMessage(`Added ${paletteFamily} node (save draft to persist)`);
  };

  const save = async () => {
    setError(null);
    try {
      const nextGraph = { ...graph, nodes, edges };
      await saveCrmVisualWorkflow(
        workflowId,
        { graph: nextGraph, expected_version: graph.workflow_version },
        CRM_WORKSPACE,
      );
      setMessage("Draft saved");
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  const validate = async () => {
    setError(null);
    try {
      const res = await validateCrmVisualWorkflow(
        workflowId,
        { ...graph, nodes, edges } as Record<string, unknown>,
        CRM_WORKSPACE,
      );
      setMessage(res.can_publish ? "Graph can publish" : "Graph has blocking issues");
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validate failed");
    }
  };

  const simulate = async () => {
    setError(null);
    try {
      const res = await simulateCrmVisualWorkflow(workflowId, {}, CRM_WORKSPACE);
      setSim(res);
      setMessage("Simulation complete (no external side effects)");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulate failed");
    }
  };

  const publish = async () => {
    setError(null);
    try {
      const res = await publishCrmVisualWorkflow(workflowId, "operator publish", CRM_WORKSPACE);
      if (!res.ok) {
        setError("Publish blocked by validation");
        return;
      }
      setMessage("Published. Active runs stay pinned to prior versions.");
      await data.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    }
  };

  const startRun = async () => {
    setError(null);
    try {
      const res = await createCrmVisualRun({ workflow_id: workflowId }, CRM_WORKSPACE);
      const id = String((res.run as { id?: string })?.id || "");
      if (id) window.location.href = `/crm/runs/${id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create run failed");
    }
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1}>
        <Box>
          <Typography variant="h6">{String(graph.name || "Workflow")}</Typography>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
            <CrmStatusBadge state={String(graph.status || "draft")} />
            <Typography variant="caption" color="text.secondary">
              version {String(graph.workflow_version ?? 1)}
            </Typography>
          </Stack>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button size="small" variant={view === "canvas" ? "contained" : "outlined"} onClick={() => setView("canvas")}>
            Canvas
          </Button>
          <Button size="small" variant={view === "outline" ? "contained" : "outlined"} onClick={() => setView("outline")}>
            Outline
          </Button>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="palette-family">Add node</InputLabel>
            <Select
              labelId="palette-family"
              label="Add node"
              value={paletteFamily}
              onChange={(e) => setPaletteFamily(e.target.value)}
            >
              {["trigger", "discovery", "enrich", "decision", "approval", "wait", "outreach", "reply", "stage", "booking", "human_task", "stop", "error"].map(
                (f) => (
                  <MenuItem key={f} value={f}>
                    {f}
                  </MenuItem>
                ),
              )}
            </Select>
          </FormControl>
          <Button size="small" onClick={addNode}>
            Add node
          </Button>
          <Button size="small" onClick={() => void save()}>
            Save draft
          </Button>
          <Button size="small" onClick={() => void validate()}>
            Validate
          </Button>
          <Button size="small" onClick={() => void simulate()}>
            Simulate
          </Button>
          <Button size="small" variant="contained" onClick={() => void publish()}>
            Publish
          </Button>
          <Button size="small" onClick={() => void startRun()}>
            Start run
          </Button>
          <Button size="small" component={Link} href="/crm/workflows">
            Back
          </Button>
        </Stack>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {validation && !(validation as { can_publish?: boolean }).can_publish ? (
        <Alert severity="warning">
          Blocking issues:{" "}
          {((validation as { issues?: Array<{ message?: string }> }).issues || [])
            .filter((i) => true)
            .slice(0, 5)
            .map((i) => i.message)
            .join(" · ") || "see inspector"}
        </Alert>
      ) : null}

      {data.isLoading ? (
        <Typography color="text.secondary">Loading workflow graph...</Typography>
      ) : (
        <Stack direction={{ xs: "column", lg: "row" }} spacing={2} alignItems="stretch">
          <Card variant="outlined" sx={{ flex: 1 }}>
            <CardContent>
              {view === "outline" ? (
                <OutlineEditor nodes={nodes} edges={edges} selectedId={selectedId} onSelect={setSelectedId} />
              ) : (
                <ReactFlowProvider>
                  <CanvasInner
                    nodes={nodes}
                    edges={edges}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                    onNodeMoved={onNodeMoved}
                  />
                </ReactFlowProvider>
              )}
            </CardContent>
          </Card>
          <Card variant="outlined" sx={{ width: { xs: "100%", lg: 360 }, flexShrink: 0 }}>
            <CrmNodeInspector workflowId={workflowId} nodeId={selectedId} mode="design" />
          </Card>
        </Stack>
      )}

      {sim ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Simulation result
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              External side effects: {String(sim.external_side_effects)}
            </Typography>
            <Box sx={{ mt: 1 }}>
              <StructuredDataView value={sim} />
            </Box>
          </CardContent>
        </Card>
      ) : null}

      <Typography variant="caption" color="text.secondary">
        Canvas supports pan/zoom/fit/minimap, node drag positions, palette add, outline editor, validate,
        simulate, and Soft Wall publish. Full multi-select, undo/redo, and auto-layout polish remain deferred.
        Credentials are references only.
      </Typography>
    </Stack>
  );
}

export default CrmWorkflowCanvasInner;

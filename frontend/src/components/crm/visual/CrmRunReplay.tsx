"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import {
  Background,
  Controls,
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
import useReducedMotion from "@/components/crm/visual/useReducedMotion";
import { CRM_WORKSPACE } from "@/components/crm/types";
import { fetchCrmVisualRun, fetchCrmVisualRunEvents, stepCrmVisualRun } from "@/lib/crm-api";

type Props = { runId: string };

function stateColor(state: string): string {
  if (state === "succeeded") return "#2e7d32";
  if (state === "failed") return "#c62828";
  if (state === "active") return "#1565c0";
  if (state === "waiting" || state === "approval_required") return "#ef6c00";
  if (state === "suppressed" || state === "cancelled") return "#616161";
  return "#9e9e9e";
}

export default function CrmRunReplay({ runId }: Props) {
  const reduced = useReducedMotion();
  const [error, setError] = React.useState<string | null>(null);
  const [paused, setPaused] = React.useState(false);
  const [follow, setFollow] = React.useState(true);
  const [selectedNode, setSelectedNode] = React.useState<string | null>(null);
  const [cursor, setCursor] = React.useState(0);
  const [speedMs, setSpeedMs] = React.useState(2000);

  const snap = useSWR(["crm-run", CRM_WORKSPACE, runId], () => fetchCrmVisualRun(runId, CRM_WORKSPACE), {
    refreshInterval: follow && !paused ? speedMs : 0,
  });

  React.useEffect(() => {
    if (!follow || paused) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const page = await fetchCrmVisualRunEvents(runId, cursor, CRM_WORKSPACE);
        if (cancelled) return;
        if ((page.events || []).length > 0) {
          setCursor(page.cursor);
          await snap.mutate();
        }
      } catch {
        /* polling fallback remains via SWR */
      }
    };
    const id = window.setInterval(() => void tick(), speedMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [cursor, follow, paused, runId, speedMs, snap]);

  const run = snap.data?.run;
  const nodeStates = snap.data?.node_states || {};
  const timeline = snap.data?.timeline || [];
  const graph = (snap.data?.graph || {}) as {
    id?: string;
    nodes?: Array<Record<string, unknown>>;
    edges?: Array<Record<string, unknown>>;
  };
  const workflowId = String(run?.workflow_id || graph.id || "");

  const nodes: Node[] = (graph.nodes || []).map((n) => {
    const id = String(n.id);
    const st = String((nodeStates[id] || {}).state || "upcoming");
    return {
      id,
      position: { x: Number(n.x || 0), y: Number(n.y || 0) },
      data: { label: `${String(n.label || n.type || id)}\n${st}` },
      style: {
        border: `2px solid ${stateColor(st)}`,
        borderRadius: 8,
        padding: 8,
        background: "#fff",
        fontSize: 12,
        whiteSpace: "pre-line",
        minWidth: 140,
        boxShadow: !reduced && st === "active" ? "0 0 0 2px rgba(21,101,192,0.25)" : undefined,
      },
    };
  });
  const edges: Edge[] = (graph.edges || []).map((e) => ({
    id: String(e.id),
    source: String(e.source),
    target: String(e.target),
    label: String(e.condition_label || ""),
  }));

  const step = async () => {
    setError(null);
    try {
      await stepCrmVisualRun(runId, CRM_WORKSPACE);
      await snap.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Step failed");
    }
  };

  const jumpFailure = () => {
    const failed = timeline.find((t) => t.state === "failed");
    if (failed?.node_id) setSelectedNode(String(failed.node_id));
  };

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1}>
        <Box>
          <Typography variant="h6">Run {runId}</Typography>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
            <CrmStatusBadge state={String(run?.status || "ready")} />
            <Typography variant="caption" color="text.secondary">
              workflow {workflowId} · v{String(run?.workflow_version ?? 1)} · cursor {String(run?.cursor ?? 0)}
            </Typography>
          </Stack>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button size="small" variant={follow ? "contained" : "outlined"} onClick={() => setFollow((v) => !v)}>
            {follow ? "Following" : "Live off"}
          </Button>
          <Button size="small" onClick={() => setPaused((v) => !v)}>
            {paused ? "Resume" : "Pause visual"}
          </Button>
          <Button size="small" onClick={() => setSpeedMs((s) => (s === 2000 ? 800 : 2000))}>
            Speed {speedMs === 800 ? "fast" : "normal"}
          </Button>
          <Button size="small" onClick={() => void step()}>
            Step forward
          </Button>
          <Button size="small" onClick={jumpFailure}>
            Jump to failure
          </Button>
          <Button size="small" component={Link} href={workflowId ? `/crm/workflows/${workflowId}` : "/crm/workflows"}>
            Workflow
          </Button>
        </Stack>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {reduced ? (
        <Alert severity="info">Reduced motion on. Static timeline and labels carry full state; no fake idle loops.</Alert>
      ) : null}

      {snap.isLoading && !snap.data ? (
        <Typography color="text.secondary">Loading run...</Typography>
      ) : (
        <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
          <Card variant="outlined" sx={{ flex: 1 }}>
            <CardContent>
              <Box sx={{ height: 420 }} aria-label="Run graph">
                <ReactFlowProvider>
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    fitView
                    onNodeClick={(_, n) => setSelectedNode(n.id)}
                    nodesDraggable={false}
                    nodesConnectable={false}
                  >
                    <Background />
                    <Controls />
                  </ReactFlow>
                </ReactFlowProvider>
              </Box>
            </CardContent>
          </Card>
          <Card variant="outlined" sx={{ width: { xs: "100%", lg: 360 } }}>
            <CrmNodeInspector
              workflowId={workflowId}
              nodeId={selectedNode}
              mode="replay"
              runId={runId}
            />
          </Card>
        </Stack>
      )}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Static timeline (always available)
          </Typography>
          <Table size="small" aria-label="Run event timeline">
            <TableHead>
              <TableRow>
                <TableCell>Seq</TableCell>
                <TableCell>Node</TableCell>
                <TableCell>State</TableCell>
                <TableCell>Time</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {timeline.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4}>No events yet</TableCell>
                </TableRow>
              ) : (
                timeline.map((row) => (
                  <TableRow
                    key={String(row.seq)}
                    hover
                    selected={selectedNode === row.node_id}
                    onClick={() => row.node_id && setSelectedNode(String(row.node_id))}
                    sx={{ cursor: row.node_id ? "pointer" : "default" }}
                  >
                    <TableCell>{String(row.seq)}</TableCell>
                    <TableCell>{String(row.label || row.node_id || "-")}</TableCell>
                    <TableCell>
                      <CrmStatusBadge state={String(row.state)} />
                    </TableCell>
                    <TableCell>{String(row.timestamp || "")}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Stack>
  );
}

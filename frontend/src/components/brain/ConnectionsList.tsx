"use client";

import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import type { BrainGraphData, GraphNode } from "@/types/brain-graph";

type Props = {
  kind: string;
  id: string;
  onNavigateTo: (node: GraphNode) => void;
  graphData?: BrainGraphData | null;
};

function relationFor(graph: BrainGraphData, node: GraphNode, selectedKey: string): string {
  const edge = graph.edges.find((item) => {
    const source = `${item.source_kind}:${item.source_id}`;
    const target = `${item.target_kind}:${item.target_id}`;
    return (source === selectedKey && target === `${node.kind}:${node.id}`) || (target === selectedKey && source === `${node.kind}:${node.id}`);
  });
  return edge?.relation || "connected";
}

function neighboursFromGraph(graph: BrainGraphData, kind: string, id: string): GraphNode[] {
  const selectedKey = `${kind}:${id}`;
  const connectedIds = new Set<string>();
  for (const edge of graph.edges) {
    const source = `${edge.source_kind}:${edge.source_id}`;
    const target = `${edge.target_kind}:${edge.target_id}`;
    if (source === selectedKey) connectedIds.add(target);
    if (target === selectedKey) connectedIds.add(source);
  }
  return graph.nodes.filter((node) => connectedIds.has(`${node.kind}:${node.id}`));
}

export default function ConnectionsList({ kind, id, onNavigateTo, graphData }: Props) {
  const [graph, setGraph] = React.useState<BrainGraphData | null>(graphData ?? null);
  const [expanded, setExpanded] = React.useState(false);
  React.useEffect(() => {
    if (graphData) {
      setGraph(graphData);
      return undefined;
    }
    let cancelled = false;
    ceApi(`/api/brain/graph/neighbours/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Failed to load neighbours");
        const payload = (await response.json()) as BrainGraphData;
        if (!cancelled) setGraph(payload);
      })
      .catch(() => {
        if (!cancelled) setGraph({ nodes: [], edges: [], total_nodes: 0, total_edges: 0, truncated: false });
      });
    return () => {
      cancelled = true;
    };
  }, [graphData, id, kind]);

  const selectedKey = `${kind}:${id}`;
  const neighbours = graph ? neighboursFromGraph(graph, kind, id) : [];
  const visible = expanded ? neighbours : neighbours.slice(0, 10);
  const groups = visible.reduce<Record<string, GraphNode[]>>((acc, node) => {
    acc[node.kind] = [...(acc[node.kind] || []), node];
    return acc;
  }, {});

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2">Connected to ({neighbours.length})</Typography>
      {Object.entries(groups).map(([group, rows]) => (
        <Box key={group}>
          <Chip size="small" label={group} sx={{ mb: 0.5 }} />
          <Stack spacing={0.5}>
            {rows.map((node) => (
              <Stack key={`${node.kind}:${node.id}`} direction="row" spacing={1} alignItems="center">
                <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                  {node.label}
                </Typography>
                <Chip size="small" variant="outlined" label={graph ? relationFor(graph, node, selectedKey) : "connected"} />
                <IconButton size="small" onClick={() => onNavigateTo(node)} aria-label={`Open ${node.label}`}>
                  <ArrowForwardIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
          </Stack>
        </Box>
      ))}
      {neighbours.length > 10 ? (
        <Button size="small" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Show less" : `Show all ${neighbours.length}`}
        </Button>
      ) : null}
      {neighbours.length === 0 ? <Typography variant="body2" color="text.secondary">No first-degree connections.</Typography> : null}
    </Stack>
  );
}

"use client";

import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { GraphNode } from "@/types/brain-graph";

function value(node: GraphNode, key: string): string | undefined {
  const content = (node as GraphNode & { content?: Record<string, unknown> }).content;
  const raw = content?.[key] ?? node.metadata?.[key];
  return typeof raw === "string" ? raw : undefined;
}

function GenericContent({ node }: { node: GraphNode }) {
  return (
    <Stack spacing={1.25}>
      <Typography variant="caption" color="text.secondary">
        Created {new Date(node.created_at).toLocaleString()}
      </Typography>
      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
        {value(node, "content") || value(node, "description") || value(node, "summary") || node.summary || "No content available."}
      </Typography>
      {Object.keys(node.metadata || {}).length ? (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {Object.entries(node.metadata).slice(0, 8).map(([key, val]) => (
            <Chip key={key} size="small" variant="outlined" label={`${key}: ${String(val)}`} />
          ))}
        </Stack>
      ) : null}
    </Stack>
  );
}

function ToolContent({ node }: { node: GraphNode }) {
  return (
    <Stack spacing={1.25}>
      <Typography variant="body2">{node.id}</Typography>
      <Typography variant="body2" color="text.secondary">
        {node.summary || "Built-in Keprix tool."}
      </Typography>
      <Chip size="small" label="Read only" />
    </Stack>
  );
}

function DeletedContent() {
  return (
    <Typography variant="body2" color="text.secondary">
      This source record has been deleted. Its graph edges are preserved so historical relationships do not break.
    </Typography>
  );
}

export function renderPanelContent(node: GraphNode) {
  if (node.deleted) return <DeletedContent />;
  if (node.kind === "tool") return <ToolContent node={node} />;
  return <GenericContent node={node} />;
}

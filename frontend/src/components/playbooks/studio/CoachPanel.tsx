"use client";

import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import type { StudioCanvas, StudioNode, StudioNodeType } from "@/lib/playbook-studio/canvas-types";
import { fetchCoachSuggestions } from "@/lib/playbook-studio/playbook-studio-api";

export default function CoachPanel({
  canvas,
  selectedNode,
  onAdd,
}: {
  canvas: StudioCanvas;
  selectedNode: StudioNode | null;
  onAdd: (nodeType: StudioNodeType, data: Record<string, unknown>) => void;
}) {
  const { data = [] } = useSWR(["studio-coach", selectedNode?.id, canvas.nodes.length, canvas.edges.length], () =>
    fetchCoachSuggestions(canvas, selectedNode?.id || null),
  );
  return (
    <Box sx={{ p: 2, borderTop: "1px solid", borderColor: "divider", display: "grid", gap: 1 }}>
      <Typography variant="subtitle2">Coach</Typography>
      {data.map((suggestion) => (
        <Box key={`${suggestion.node_type}-${suggestion.label}`} sx={{ display: "grid", gap: 0.5 }}>
          <Typography variant="body2" fontWeight={600}>
            {suggestion.label}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {suggestion.reason}
          </Typography>
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => onAdd(suggestion.node_type as StudioNodeType, suggestion.prefilled_data)}
          >
            Add
          </Button>
        </Box>
      ))}
    </Box>
  );
}

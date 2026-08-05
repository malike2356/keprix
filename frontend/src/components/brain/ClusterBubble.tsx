"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import type { NodeProps } from "@xyflow/react";
import { nodeKindMeta } from "@/components/brain/nodes/node-kinds";
import type { BrainNodeKind } from "@/types/brain-graph";

export type ClusterBubbleData = {
  label: string;
  dominantKind: BrainNodeKind;
  width: number;
  height: number;
};

export default function ClusterBubble({ data }: NodeProps) {
  const bubble = data as ClusterBubbleData;
  const color = nodeKindMeta[bubble.dominantKind]?.color ?? "#64748b";

  return (
    <Box
      sx={{
        width: bubble.width,
        height: bubble.height,
        border: "1px dashed",
        borderColor: alpha(color, 0.35),
        bgcolor: (theme) => alpha(color, theme.palette.mode === "dark" ? 0.08 : 0.06),
        borderRadius: 2,
        pointerEvents: "none",
        position: "relative",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          position: "absolute",
          top: 8,
          left: 10,
          color: alpha(color, 0.9),
          textTransform: "none",
          fontWeight: 500,
          letterSpacing: 0.2,
        }}
      >
        {bubble.label}
      </Typography>
    </Box>
  );
}

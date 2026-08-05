"use client";

import Box from "@mui/material/Box";
import StarIcon from "@mui/icons-material/Star";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { BrainFlowNodeData, BrainNodeKind } from "@/types/brain-graph";
import { nodeKindMeta } from "@/components/brain/nodes/node-kinds";

type Props = NodeProps & {
  kind: BrainNodeKind | "deleted";
};

export default function BrainNodeBase({ data, selected, kind }: Props) {
  const node = data as BrainFlowNodeData;
  const meta = kind === "deleted" ? null : nodeKindMeta[kind];
  const color = kind === "deleted" ? "#94a3b8" : meta?.color ?? "#64748b";
  const Icon = meta?.Icon;
  const size = node.size ?? 44;
  const shape = kind === "deleted" ? "rounded" : meta?.shape;
  const clipPath = shape === "hexagon"
    ? "polygon(25% 4%, 75% 4%, 100% 50%, 75% 96%, 25% 96%, 0 50%)"
    : shape === "folded"
      ? "polygon(0 0, 78% 0, 100% 22%, 100% 100%, 0 100%)"
      : undefined;
  const rotate = shape === "diamond" ? "rotate(45deg)" : undefined;
  const innerRotate = shape === "diamond" ? "rotate(-45deg)" : undefined;

  const healthBorder = node.healthOrphan
    ? "#ef4444"
    : node.healthDuplicate
      ? "#f97316"
      : selected
        ? color
        : alpha(color, 0.45);
  const accent = node.healthStale ? "#94a3b8" : color;

  return (
    <Tooltip title={node.summary || node.label} arrow placement="top">
      <Box sx={{ position: "relative" }}>
        {node.healthHub ? (
          <StarIcon
            sx={{
              position: "absolute",
              top: -8,
              right: -8,
              fontSize: 16,
              color: "warning.main",
              zIndex: 2,
            }}
          />
        ) : null}
        {node.healthOrphan ? (
          <WarningAmberIcon
            sx={{
              position: "absolute",
              top: -8,
              left: -8,
              fontSize: 16,
              color: "error.main",
              zIndex: 2,
            }}
          />
        ) : null}
      <Box
        sx={{
          width: size,
          height: shape === "rounded" ? Math.max(36, size * 0.72) : size,
          bgcolor: (theme) => alpha(accent, theme.palette.mode === "dark" ? 0.18 : 0.12),
          color: accent,
          border: node.healthDuplicate ? "1.5px dashed" : "1px solid",
          borderColor: healthBorder,
          borderRadius: shape === "circle" ? "50%" : shape === "square" || shape === "diamond" ? 1 : 1.5,
          clipPath,
          transform: rotate,
          opacity: node.dimmed ? 0.22 : 1,
          boxShadow: node.active
            ? `0 0 0 6px ${alpha(accent, 0.18)}`
            : selected || node.highlighted
              ? `0 0 0 3px ${alpha(accent, 0.22)}`
              : "none",
          animation: node.active ? "brainPulse 900ms ease-in-out 1" : undefined,
          "@keyframes brainPulse": {
            "0%": { transform: rotate ? `${rotate} scale(1)` : "scale(1)" },
            "40%": { transform: rotate ? `${rotate} scale(1.08)` : "scale(1.08)" },
            "100%": { transform: rotate ? `${rotate} scale(1)` : "scale(1)" },
          },
          display: "grid",
          placeItems: "center",
          transition: "opacity 140ms ease, box-shadow 140ms ease, border-color 140ms ease",
        }}
      >
        <Handle
          type="target"
          position={Position.Top}
          style={{ opacity: 0, width: 1, height: 1, top: "50%", left: "50%", transform: "translate(-50%, -50%)", border: "none" }}
        />
        <Box
          sx={{
            transform: innerRotate,
            width: "88%",
            display: "grid",
            placeItems: "center",
            gap: 0.2,
            textAlign: "center",
          }}
        >
          {Icon ? <Icon sx={{ fontSize: Math.max(13, size * 0.24), opacity: 0.92 }} /> : null}
          <Typography
            variant="caption"
            sx={{
              fontSize: 10,
              lineHeight: 1.05,
              maxWidth: size * 0.8,
              fontWeight: 500,
              color: "text.primary",
            }}
            noWrap
          >
            {node.deleted ? "[deleted]" : node.label}
          </Typography>
        </Box>
        <Handle
          type="source"
          position={Position.Bottom}
          style={{ opacity: 0, width: 1, height: 1, top: "50%", left: "50%", transform: "translate(-50%, -50%)", border: "none" }}
        />
      </Box>
      </Box>
    </Tooltip>
  );
}

"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { alpha, useTheme } from "@mui/material/styles";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { StudioNodeData, StudioNodeType } from "@/lib/playbook-studio/canvas-types";
import { nodeDefinition } from "@/lib/playbook-studio/node-registry";

type Props = NodeProps & {
  type: StudioNodeType;
  data: StudioNodeData & { invalid?: boolean };
  invalid?: boolean;
  conditionHandles?: boolean;
};

export default function StudioNodeBase({ type, data, selected, invalid, conditionHandles }: Props) {
  const theme = useTheme();
  const definition = nodeDefinition(type);
  const Icon = definition.icon;
  const label = data.label || definition.label;
  const headerSx =
    definition.color === "default"
      ? {
          bgcolor: alpha(theme.palette.text.primary, theme.palette.mode === "dark" ? 0.08 : 0.06),
          color: "text.primary",
        }
      : {
          bgcolor: alpha(
            (theme.palette[definition.color] || theme.palette.primary).main,
            theme.palette.mode === "dark" ? 0.22 : 0.14,
          ),
          color: "text.primary",
        };
  const runBorder = data.runStatus === "completed"
    ? "success.main"
    : data.runStatus === "failed"
      ? "error.main"
      : data.runStatus === "waiting_approval"
        ? "warning.main"
        : data.runStatus === "running"
          ? "primary.main"
          : null;
  return (
    <Box
      sx={{
        width: 220,
        minHeight: 88,
        bgcolor: "background.paper",
        color: "text.primary",
        border: "1px solid",
        borderColor: invalid || data.invalid ? "error.main" : runBorder || (selected ? "primary.main" : "divider"),
        borderWidth: selected ? 2 : 1,
        borderRadius: 1,
        boxShadow: selected ? 3 : 1,
        overflow: "hidden",
      }}
    >
      <Handle type="target" position={Position.Left} />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 1,
          py: 0.75,
          ...headerSx,
        }}
      >
        <Icon fontSize="small" />
        <Typography variant="subtitle2" noWrap>
          {label}
        </Typography>
      </Box>
      <Box sx={{ px: 1, py: 1 }}>
        <Chip size="small" label={definition.label} color={definition.color} variant="outlined" />
      </Box>
      {conditionHandles ? (
        <>
          <Handle id="true" type="source" position={Position.Right} style={{ top: 32 }} />
          <Handle id="false" type="source" position={Position.Right} style={{ top: 68 }} />
        </>
      ) : (
        <Handle type="source" position={Position.Right} />
      )}
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import { STUDIO_NODE_DEFINITIONS } from "@/lib/playbook-studio/node-registry";
import type { StudioNodeType } from "@/lib/playbook-studio/canvas-types";

export default function NodePalette() {
  const onDragStart = (event: React.DragEvent, type: StudioNodeType) => {
    event.dataTransfer.setData("application/reactflow", type);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Nodes
      </Typography>
      <Box sx={{ display: "grid", gap: 1 }}>
        {STUDIO_NODE_DEFINITIONS.map((definition) => {
          const Icon = definition.icon;
          return (
            <ButtonBase
              key={definition.type}
              draggable
              onDragStart={(event) => onDragStart(event, definition.type)}
              sx={{
                justifyContent: "flex-start",
                gap: 1,
                p: 1,
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                textAlign: "left",
              }}
            >
              <Icon fontSize="small" color={definition.color === "default" ? "inherit" : definition.color} />
              <Typography variant="body2">{definition.label}</Typography>
            </ButtonBase>
          );
        })}
      </Box>
      <Divider sx={{ my: 2 }} />
      <Typography variant="caption" color="text.secondary">
        Drag nodes onto the canvas.
      </Typography>
    </Box>
  );
}

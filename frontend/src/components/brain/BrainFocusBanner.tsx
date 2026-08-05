"use client";

import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { GraphNode } from "@/types/brain-graph";

export default function BrainFocusBanner({ node, depth, setDepth, onClear }: { node: GraphNode; depth: number; setDepth: (value: number) => void; onClear: () => void }) {
  return (
    <Paper variant="outlined" sx={{ position: "absolute", zIndex: 6, top: 12, left: 12, right: 12, p: 1 }}>
      <Stack direction="row" spacing={2} alignItems="center">
        <Typography variant="body2" sx={{ flex: 1 }} noWrap>
          ● Focused on: {node.label}
        </Typography>
        <Typography variant="caption">Depth</Typography>
        <Slider size="small" min={1} max={3} step={1} value={depth} onChange={(_, value) => setDepth(Number(value))} marks sx={{ width: 110 }} />
        <Button size="small" onClick={onClear}>Show full graph</Button>
      </Stack>
    </Paper>
  );
}

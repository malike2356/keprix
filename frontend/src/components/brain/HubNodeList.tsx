"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Link from "next/link";
import type { GraphNode } from "@/types/brain-graph";
import { nodeKindMeta } from "@/components/brain/nodes/node-kinds";

type Props = {
  nodes: GraphNode[];
  connectionCounts?: Record<string, number>;
};

export default function HubNodeList({ nodes, connectionCounts = {} }: Props) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Hub nodes (most connected)</Typography>
      {nodes.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No hub nodes yet.</Typography>
      ) : (
        <List dense>
          {nodes.map((node) => {
            const color = nodeKindMeta[node.kind]?.color ?? "#64748b";
            const key = `${node.kind}:${node.id}`;
            const connections = connectionCounts[key] ?? 0;
            return (
              <ListItem key={key} disableGutters secondaryAction={
                <Button size="small" component={Link} href="/brain/graph">View</Button>
              }>
                <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: color, mr: 1.5 }} />
                <ListItemText
                  primary={node.label}
                  secondary={`${node.kind} · ${connections || "high"} connections`}
                />
              </ListItem>
            );
          })}
        </List>
      )}
    </Box>
  );
}

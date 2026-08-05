"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import * as React from "react";
import type { GraphNode } from "@/types/brain-graph";

type Props = {
  nodes: GraphNode[];
  onDeleteAll: () => Promise<void>;
};

function ageLabel(createdAt: string): string {
  const days = Math.max(0, Math.round((Date.now() - new Date(createdAt).getTime()) / 86400000));
  return `${days} days ago`;
}

export default function OrphanNodeList({ nodes, onDeleteAll }: Props) {
  const [open, setOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const preview = nodes.slice(0, 5);

  const confirmDelete = async () => {
    setBusy(true);
    try {
      await onDeleteAll();
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Orphan nodes (no connections)
      </Typography>
      {nodes.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No orphan nodes found.</Typography>
      ) : (
        <>
          <List dense>
            {preview.map((node) => (
              <ListItem key={`${node.kind}:${node.id}`} disableGutters>
                <ListItemText
                  primary={`${node.kind}  "${node.label}"`}
                  secondary={`Created ${ageLabel(node.created_at)}`}
                />
              </ListItem>
            ))}
          </List>
          {nodes.length > preview.length ? (
            <Typography variant="caption" color="text.secondary">
              + {nodes.length - preview.length} more
            </Typography>
          ) : null}
          <Button sx={{ mt: 1 }} color="error" variant="outlined" onClick={() => setOpen(true)}>
            Delete all orphans ({nodes.length})
          </Button>
        </>
      )}

      <Dialog open={open} onClose={() => !busy && setOpen(false)}>
        <DialogTitle>Delete orphan nodes?</DialogTitle>
        <DialogContent>
          <Typography>
            This will permanently delete {nodes.length} node(s) with no graph connections.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
          <Button color="error" variant="contained" onClick={() => void confirmDelete()} disabled={busy}>
            Delete {nodes.length}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

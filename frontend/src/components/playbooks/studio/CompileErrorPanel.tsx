"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import type { StudioCompileError } from "@/lib/playbook-studio/canvas-types";

export default function CompileErrorPanel({ errors }: { errors: StudioCompileError[] }) {
  if (!errors.length) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2">Inspector</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Select a node to edit its fields.
        </Typography>
      </Box>
    );
  }
  return (
    <Box sx={{ p: 2 }}>
      <Alert severity="error" sx={{ mb: 1 }}>
        Resolve compile errors before saving or running.
      </Alert>
      <List dense>
        {errors.map((error, index) => (
          <ListItem key={`${error.code}-${index}`} disableGutters>
            <ListItemText
              primary={error.message}
              secondary={error.node_id ? `${error.code} · ${error.node_id}` : error.code}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}

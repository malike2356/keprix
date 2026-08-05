"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import * as React from "react";
import type { GraphNode } from "@/types/brain-graph";

type Props = {
  node: GraphNode;
  onSave: (body: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
};

function editableText(node: GraphNode): string {
  const full = node as GraphNode & { content?: Record<string, unknown> };
  const content = full.content?.content ?? full.content?.description ?? full.content?.body ?? node.summary;
  return typeof content === "string" ? content : "";
}

export function PanelEditForm({ node, onSave, onCancel }: Props) {
  const [title, setTitle] = React.useState(node.label);
  const [body, setBody] = React.useState(editableText(node));
  const [status, setStatus] = React.useState(String(node.metadata?.status || "open"));
  const canEdit = node.kind === "memory" || node.kind === "skill" || node.kind === "task";
  if (!canEdit) return null;
  return (
    <Box component="form" onSubmit={(event) => { event.preventDefault(); void onSave({ title, name: title, content: body, description: body, body, status }); }}>
      <Stack spacing={1.5}>
        <TextField label={node.kind === "skill" ? "Name" : "Title"} value={title} onChange={(event) => setTitle(event.target.value)} size="small" />
        {node.kind === "task" ? (
          <TextField select label="Status" value={status} onChange={(event) => setStatus(event.target.value)} size="small">
            {["open", "in_progress", "done", "blocked"].map((item) => (
              <MenuItem key={item} value={item}>{item}</MenuItem>
            ))}
          </TextField>
        ) : null}
        <TextField label="Content" value={body} onChange={(event) => setBody(event.target.value)} multiline minRows={6} />
        <Stack direction="row" spacing={1}>
          <Button type="submit" variant="contained" size="small">Save</Button>
          <Button variant="text" size="small" onClick={onCancel}>Cancel</Button>
        </Stack>
      </Stack>
    </Box>
  );
}

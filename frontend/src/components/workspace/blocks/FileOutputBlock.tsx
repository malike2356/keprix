"use client";

import DescriptionIcon from "@mui/icons-material/Description";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { openFileInEditor } from "@/lib/workspace-api";
import type { MessageBlock } from "@/lib/workspace-api";

type FileOutputBlockProps = {
  block: Extract<MessageBlock, { type: "file" }>;
  canOpen?: boolean;
};

export default function FileOutputBlock({ block, canOpen = false }: FileOutputBlockProps) {
  const [busy, setBusy] = React.useState(false);

  const onOpen = async () => {
    setBusy(true);
    try {
      await openFileInEditor(block.path);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        p: 1,
        borderRadius: 1,
        border: 1,
        borderColor: "divider",
      }}
    >
      <DescriptionIcon fontSize="small" color="action" />
      <Typography variant="body2" sx={{ flex: 1, fontFamily: "monospace" }}>
        {block.path}
      </Typography>
      <Chip size="small" label={block.action} color="info" variant="outlined" />
      {canOpen ? (
        <Button size="small" variant="text" disabled={busy} onClick={onOpen}>
          Open in editor
        </Button>
      ) : null}
    </Box>
  );
}

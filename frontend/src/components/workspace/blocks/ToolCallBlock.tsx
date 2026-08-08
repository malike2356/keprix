"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SettingsIcon from "@mui/icons-material/Settings";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { keyframes } from "@mui/material/styles";
import * as React from "react";
import StructuredDataView from "@/components/ui/StructuredDataView";
import type { MessageBlock } from "@/lib/workspace-api";

const pulse = keyframes`
  0% { opacity: 1; }
  50% { opacity: 0.45; }
  100% { opacity: 1; }
`;

type ToolCallBlockProps = {
  block: Extract<MessageBlock, { type: "tool_call" }>;
};

export default function ToolCallBlock({ block }: ToolCallBlockProps) {
  const [open, setOpen] = React.useState(block.status === "running");
  const done = block.status === "done";
  const errored = block.status === "error";

  React.useEffect(() => {
    if (done || errored) {
      setOpen(false);
    }
  }, [done, errored]);

  return (
    <Paper variant="outlined" sx={{ p: 1.25 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <SettingsIcon
          fontSize="small"
          sx={{ animation: block.status === "running" ? `${pulse} 1.2s infinite` : "none" }}
        />
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }}>
          {block.name}
        </Typography>
        {block.mode ? (
          <Chip
            size="small"
            variant="outlined"
            label={block.mode === "dry_run" ? "dry run" : "live"}
            color={block.mode === "dry_run" ? "default" : "info"}
          />
        ) : null}
        {done ? <CheckCircleIcon color="success" fontSize="small" /> : null}
        {errored ? <ErrorIcon color="error" fontSize="small" /> : null}
        <Chip
          size="small"
          label={block.status === "running" ? "Running..." : block.status === "error" ? "Error" : "Done"}
          color={block.status === "running" ? "warning" : block.status === "error" ? "error" : "success"}
        />
        <IconButton size="small" onClick={() => setOpen((value) => !value)} aria-label="Toggle tool details">
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>
      <Collapse in={open}>
        <Box sx={{ mt: 1.5, display: "grid", gap: 1 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Input
            </Typography>
            <Box
              sx={{
                m: 0,
                mt: 0.5,
                p: 1,
                borderRadius: 1,
                bgcolor: "background.paper",
                overflow: "auto",
              }}
            >
              <StructuredDataView value={block.input} emptyLabel="No input" />
            </Box>
          </Box>
          {block.output ? (
            <Box>
              <Typography variant="caption" color="text.secondary">
                Output
              </Typography>
              <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: "pre-wrap" }}>
                {block.output}
              </Typography>
            </Box>
          ) : null}
        </Box>
      </Collapse>
    </Paper>
  );
}

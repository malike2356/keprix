"use client";

import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import type { ReactNode } from "react";

type ContextPanelProps = {
  open: boolean;
  title?: string;
  onClose: () => void;
  children?: ReactNode;
};

export default function ContextPanel({ open, title = "Context", onClose, children }: ContextPanelProps) {
  return (
    <Collapse in={open} orientation="horizontal">
      <Paper
        elevation={0}
        sx={{
          width: { xs: 280, lg: 320 },
          minWidth: { xs: 280, lg: 320 },
          borderLeft: 1,
          borderColor: "divider",
          height: "100%",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1.25,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <InfoOutlinedIcon fontSize="small" color="action" />
            <Typography variant="subtitle2">{title}</Typography>
          </Box>
          <IconButton size="small" onClick={onClose} aria-label="Close context panel">
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
        <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
          {children || (
            <Typography variant="body2" color="text.secondary">
              Agent, source, job, or record context appears here.
            </Typography>
          )}
        </Box>
      </Paper>
    </Collapse>
  );
}

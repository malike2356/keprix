"use client";

import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import type { Viewport } from "@xyflow/react";
import * as React from "react";
import { exportBrainAsPNG } from "@/components/brain/BrainExportPNG";
import {
  downloadBrainEdgesCsv,
  downloadBrainJsonExport,
  downloadBrainNodesCsv,
  downloadBrainObsidianExport,
} from "@/lib/brain-export-api";

type Props = {
  canvasRef: React.RefObject<HTMLElement | null>;
  fitView: () => void | Promise<void>;
  getViewport: () => Viewport;
  setViewport: (viewport: Viewport) => void;
  workspaceId?: string;
  onShare?: () => void;
};

export default function BrainExportMenu({
  canvasRef,
  fitView,
  getViewport,
  setViewport,
  workspaceId,
  onShare,
}: Props) {
  const [anchor, setAnchor] = React.useState<HTMLElement | null>(null);
  const [busy, setBusy] = React.useState(false);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
      setAnchor(null);
    }
  };

  return (
    <Box>
      <Button
        size="small"
        variant="outlined"
        endIcon={<ArrowDropDownIcon />}
        disabled={busy}
        onClick={(event) => setAnchor(event.currentTarget)}
        sx={{
          textTransform: "none",
          fontWeight: 500,
          borderColor: "divider",
          color: "text.secondary",
          bgcolor: "transparent",
        }}
      >
        Export
      </Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        <MenuItem
          onClick={() =>
            void run(async () => {
              if (!canvasRef.current) return;
              await exportBrainAsPNG(canvasRef.current, "brain-graph-view.png", { getViewport, setViewport });
            })
          }
        >
          <ListItemText primary="PNG (current view)" />
        </MenuItem>
        <MenuItem
          onClick={() =>
            void run(async () => {
              if (!canvasRef.current) return;
              await exportBrainAsPNG(canvasRef.current, "brain-graph-full.png", {
                fullGraph: true,
                fitView,
                getViewport,
                setViewport,
              });
            })
          }
        >
          <ListItemText primary="PNG (full graph)" />
        </MenuItem>
        <MenuItem onClick={() => void run(() => downloadBrainJsonExport(workspaceId))}>
          <ListItemText primary="JSON (full data)" />
        </MenuItem>
        <MenuItem onClick={() => void run(() => downloadBrainObsidianExport(workspaceId))}>
          <ListItemText primary="Obsidian vault (ZIP)" />
        </MenuItem>
        <MenuItem onClick={() => void run(() => downloadBrainNodesCsv(workspaceId))}>
          <ListItemText primary="CSV (nodes)" />
        </MenuItem>
        <MenuItem onClick={() => void run(() => downloadBrainEdgesCsv(workspaceId))}>
          <ListItemText primary="CSV (edges)" />
        </MenuItem>
        {onShare ? <Divider key="share-divider" /> : null}
        {onShare ? (
          <MenuItem
            key="share-link"
            onClick={() => {
              setAnchor(null);
              onShare();
            }}
          >
            <ListItemText primary="Share link..." />
          </MenuItem>
        ) : null}
      </Menu>
    </Box>
  );
}

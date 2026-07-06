"use client";

import { IconDotsVertical, IconTools } from "@tabler/icons-react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/loading";
import { formatTimeAgo } from "@/lib/time-ago";
import type { AdminTool } from "@/lib/admin-workspace-api";

type ToolTableProps = {
  rows: AdminTool[];
  loading?: boolean;
  onOpen: (tool: AdminTool) => void;
  onDisable: (toolId: string) => void;
  onDelete: (toolId: string) => void;
};

function sourceChip(source: AdminTool["source"]) {
  if (source === "builtin") return <Chip size="small" label="Built-in" color="info" />;
  if (source === "community") return <Chip size="small" label="Community" color="success" />;
  return <Chip size="small" label="Synthesised" color="secondary" />;
}

export default function ToolTable({ rows, loading = false, onOpen, onDisable, onDelete }: ToolTableProps) {
  const [menuAnchor, setMenuAnchor] = React.useState<null | HTMLElement>(null);
  const [activeTool, setActiveTool] = React.useState<AdminTool | null>(null);

  if (loading) {
    return <SkeletonList rows={5} rowHeight={48} />;
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No tools found"
        description="Adjust your search or install a synthesised tool from the mutation queue."
        icon={<IconTools size={40} stroke={1.5} />}
      />
    );
  }

  return (
    <>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Source</TableCell>
            <TableCell>Last used</TableCell>
            <TableCell>Times called</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((tool) => (
            <TableRow key={tool.id} hover>
              <TableCell>
                <Typography
                  component="button"
                  onClick={() => onOpen(tool)}
                  sx={{
                    border: 0,
                    background: "none",
                    cursor: "pointer",
                    fontFamily: "monospace",
                    color: "primary.main",
                    p: 0,
                  }}
                >
                  {tool.name}
                </Typography>
              </TableCell>
              <TableCell>{tool.description}</TableCell>
              <TableCell>{sourceChip(tool.source)}</TableCell>
              <TableCell>{formatTimeAgo(tool.last_used_at) || "Never"}</TableCell>
              <TableCell>{tool.times_called}</TableCell>
              <TableCell>
                <Chip
                  size="small"
                  label={tool.status === "active" ? "Active" : "Disabled"}
                  color={tool.status === "active" ? "success" : "default"}
                />
              </TableCell>
              <TableCell align="right">
                <IconButton
                  size="small"
                  onClick={(event) => {
                    setMenuAnchor(event.currentTarget);
                    setActiveTool(tool);
                  }}
                >
                  <IconDotsVertical size={18} stroke={1.75} />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}>
        <MenuItem
          onClick={() => {
            if (activeTool) onOpen(activeTool);
            setMenuAnchor(null);
          }}
        >
          View code
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (activeTool) onDisable(activeTool.id);
            setMenuAnchor(null);
          }}
        >
          Disable
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (activeTool) onDelete(activeTool.id);
            setMenuAnchor(null);
          }}
        >
          Delete
        </MenuItem>
      </Menu>
    </>
  );
}

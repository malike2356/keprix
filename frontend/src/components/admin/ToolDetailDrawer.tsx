"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import dynamic from "next/dynamic";
import * as React from "react";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import { formatTimeAgo } from "@/lib/time-ago";
import type { AdminTool } from "@/lib/admin-workspace-api";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type ToolDetailDrawerProps = {
  tool: AdminTool | null;
  open: boolean;
  onClose: () => void;
  onDisable: (toolId: string) => void;
  onDelete: (toolId: string) => void;
};

export default function ToolDetailDrawer({ tool, open, onClose, onDisable, onDelete }: ToolDetailDrawerProps) {
  const [tab, setTab] = React.useState(0);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  if (!tool) return null;

  const usage = tool.usage || { labels: [], values: [] };

  return (
    <>
      <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 520 } } }}>
        <Box sx={{ p: 3, display: "flex", flexDirection: "column", height: "100%" }}>
          <Typography variant="h6">{tool.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {tool.description}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, my: 2 }}>
            <Chip size="small" label={tool.source} />
            <Chip size="small" label={tool.status} color={tool.status === "active" ? "success" : "default"} />
          </Box>
          <Typography variant="caption" color="text.secondary">
            Created {formatTimeAgo(tool.created_at) || "unknown"} | Last used {formatTimeAgo(tool.last_used_at) || "never"}
          </Typography>

          <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mt: 2 }}>
            <Tab label="Code" />
            <Tab label="Skill YAML" />
            <Tab label="Usage" />
          </Tabs>

          <Box sx={{ flex: 1, overflow: "auto", mt: 2 }}>
            {tab === 0 ? <CodeBlock language="python" content={tool.tool_code || "# No code available"} /> : null}
            {tab === 1 ? <CodeBlock language="yaml" content={tool.skill_yaml || "# No skill file"} /> : null}
            {tab === 2 ? (
              <Chart
                type="area"
                height={220}
                series={[{ name: "Calls", data: usage.values }]}
                options={{
                  chart: { toolbar: { show: false }, sparkline: { enabled: false } },
                  xaxis: { categories: usage.labels },
                  stroke: { curve: "smooth", width: 2 },
                  dataLabels: { enabled: false },
                }}
              />
            ) : null}
          </Box>

          <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
            <Button variant="outlined" color="error" onClick={() => onDisable(tool.id)}>
              Disable tool
            </Button>
            <Button variant="contained" color="error" onClick={() => setConfirmOpen(true)}>
              Delete tool
            </Button>
          </Box>
        </Box>
      </Drawer>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Delete tool?</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            This removes {tool.name} from the active tool library.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => {
              onDelete(tool.id);
              setConfirmOpen(false);
              onClose();
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

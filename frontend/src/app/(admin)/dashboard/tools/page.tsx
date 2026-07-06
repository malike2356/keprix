"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import * as React from "react";
import useSWR from "swr";
import ToolDetailDrawer from "@/components/admin/ToolDetailDrawer";
import ToolTable from "@/components/admin/ToolTable";
import DashboardCard from "@/components/cards/DashboardCard";
import PageContainer from "@/components/shared/PageContainer";
import {
  deleteAdminTool,
  disableAdminTool,
  fetchAdminTool,
  fetchAdminTools,
  type AdminTool,
} from "@/lib/admin-workspace-api";

const TABS = [
  { key: "all", label: "All tools" },
  { key: "builtin", label: "Built-in" },
  { key: "synthesised", label: "Synthesised" },
] as const;

export default function AdminToolsPage() {
  const [tab, setTab] = React.useState<(typeof TABS)[number]["key"]>("all");
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<AdminTool | null>(null);
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const { data, isLoading, mutate } = useSWR(["admin-tools", tab, search], () =>
    fetchAdminTools(search, tab),
  );

  const openTool = async (tool: AdminTool) => {
    const detail = await fetchAdminTool(tool.id);
    setSelected(detail);
    setDrawerOpen(true);
  };

  return (
    <PageContainer title="Tool Library" description="Installed built-in and synthesised tools." padded={false}>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <TextField
            size="small"
            placeholder="Search tools..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            sx={{ minWidth: 260 }}
          />
          <Tooltip title="Coming in v1.1">
            <span>
              <Button variant="outlined" disabled>
                Install from registry
              </Button>
            </span>
          </Tooltip>
        </Box>

        <Tabs value={tab} onChange={(_, value) => setTab(value)}>
          {TABS.map((item) => (
            <Tab
              key={item.key}
              value={item.key}
              label={`${item.label} (${data?.counts?.[item.key] ?? 0})`}
            />
          ))}
        </Tabs>

        <DashboardCard title="Installed tools">
          <ToolTable
            rows={data?.items || []}
            loading={isLoading}
            onOpen={(tool) => void openTool(tool)}
            onDisable={(toolId) => {
              void disableAdminTool(toolId).then(() => mutate());
            }}
            onDelete={(toolId) => {
              void deleteAdminTool(toolId).then(() => mutate());
            }}
          />
        </DashboardCard>
      </Box>

      <ToolDetailDrawer
        tool={selected}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onDisable={(toolId) => void disableAdminTool(toolId).then(() => mutate())}
        onDelete={(toolId) => void deleteAdminTool(toolId).then(() => mutate())}
      />
    </PageContainer>
  );
}

"use client";

import Box from "@mui/material/Box";
import * as React from "react";
import { SessionProvider, useRequireSession } from "@/lib/ce-auth";
import { AdminHeader } from "@/components/admin/AdminHeader";
import { AdminSidebar, useAdminSidebarCollapsed } from "@/components/admin/Sidebar";
import CommandPalette from "@/components/shared/CommandPalette";
import WorkspaceFooter from "@/components/shell/WorkspaceFooter";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { WorkspaceThemeRestore } from "@/components/providers/WorkspaceThemeRestore";

function AdminLayoutInner({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [collapsed, toggleCollapsed] = useAdminSidebarCollapsed();
  const { open, openPalette, closePalette } = useCommandPalette();

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <AdminSidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
      />
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <AdminHeader
          collapsed={collapsed}
          onMenuClick={() => setMobileOpen(true)}
          onCommandPaletteOpen={openPalette}
        />
        <CommandPalette open={open} onClose={closePalette} />
        <Box sx={{ display: "flex", flex: 1, flexDirection: "column", minHeight: 0 }}>
          <Box component="main" sx={{ flex: 1, p: { xs: 2, md: 3 }, overflow: "auto", bgcolor: "background.default" }}>
            <Box sx={{ width: "100%" }}>{children}</Box>
          </Box>
          <WorkspaceFooter />
        </Box>
      </Box>
    </Box>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <WorkspaceThemeRestore />
      <AdminLayoutInner>{children}</AdminLayoutInner>
    </SessionProvider>
  );
}

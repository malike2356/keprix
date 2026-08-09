"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react";
import { usePathname } from "next/navigation";
import * as React from "react";
import KeprixLogo from "@/components/shared/KeprixLogo";
import Scrollbar from "@/components/shared/Scrollbar";
import useSWR from "swr";
import {
  ADMIN_NAV_ITEMS,
  ADMIN_SIDEBAR_COLLAPSED_KEY,
  ADMIN_SIDEBAR_COLLAPSED_WIDTH,
  ADMIN_SIDEBAR_WIDTH,
} from "./admin-nav";
import { fetchMutationStats } from "@/lib/mutation-api";

type AdminSidebarProps = {
  mobileOpen: boolean;
  onMobileClose: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function AdminSidebar({
  mobileOpen,
  onMobileClose,
  collapsed,
  onToggleCollapsed,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const { data: mutationStats } = useSWR("mutation-stats-nav", fetchMutationStats, {
    refreshInterval: 30_000,
  });
  const pendingCount = mutationStats?.staged ?? 0;
  const width = collapsed ? ADMIN_SIDEBAR_COLLAPSED_WIDTH : ADMIN_SIDEBAR_WIDTH;

  const content = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <Box sx={{ flexShrink: 0, px: collapsed ? 1 : 2.5, py: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Box component="a" href="/home" sx={{ textDecoration: "none", color: "inherit", minWidth: 0 }}>
          <KeprixLogo variant={collapsed ? "icon" : "full"} size="md" />
        </Box>
        <IconButton size="small" onClick={onToggleCollapsed} sx={{ display: { xs: "none", md: "inline-flex" } }}>
          {collapsed ? <IconChevronRight size={18} stroke={1.75} /> : <IconChevronLeft size={18} stroke={1.75} />}
        </IconButton>
      </Box>
      <Divider />
      <Scrollbar sx={{ flex: 1, py: 1 }}>
        <List dense disablePadding>
          {ADMIN_NAV_ITEMS.map((entry, index) => {
            if (entry.type === "subheader") {
              if (collapsed) return null;
              return (
                <Typography
                  key={`${entry.title}-${index}`}
                  variant="overline"
                  sx={{ px: 2.5, py: 1, display: "block", color: "text.secondary" }}
                >
                  {entry.title}
                </Typography>
              );
            }
            const normalizedPath = pathname?.replace(/^\/dashboard/, "/admin") ?? "";
            const active =
              normalizedPath === entry.href || normalizedPath.startsWith(`${entry.href}/`);
            const Icon = entry.icon;
            const badge = entry.badgeKey === "pendingMutations" && pendingCount > 0 ? pendingCount : null;
            const button = (
              <ListItemButton
                component="a"
                href={entry.href}
                selected={active}
                onClick={onMobileClose}
                sx={{ mx: 1, borderRadius: 1, justifyContent: collapsed ? "center" : "flex-start" }}
              >
                <ListItemIcon sx={{ minWidth: collapsed ? 0 : 36, justifyContent: "center", color: "inherit" }}>
                  <Icon size={20} stroke={1.75} />
                </ListItemIcon>
                {!collapsed ? (
                  <ListItemText
                    primary={entry.title}
                    primaryTypographyProps={{ variant: "body2" }}
                  />
                ) : null}
                {!collapsed && badge ? <Chip size="small" color="warning" label={badge} /> : null}
              </ListItemButton>
            );
            return (
              <Box key={entry.href}>
                {collapsed ? (
                  <Tooltip title={entry.title} placement="right">
                    {button}
                  </Tooltip>
                ) : (
                  button
                )}
              </Box>
            );
          })}
        </List>
      </Scrollbar>
    </Box>
  );

  return (
    <>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { width: ADMIN_SIDEBAR_WIDTH, height: "100vh", overflow: "hidden" },
        }}
      >
        {content}
      </Drawer>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: "none", md: "block" },
          width,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width,
            boxSizing: "border-box",
            height: "100vh",
            overflow: "hidden",
            borderRight: 1,
            borderColor: "divider",
          },
        }}
      >
        {content}
      </Drawer>
    </>
  );
}

export function useAdminSidebarCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    setCollapsed(localStorage.getItem(ADMIN_SIDEBAR_COLLAPSED_KEY) === "1");
  }, []);

  const toggle = React.useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(ADMIN_SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      return next;
    });
  }, []);

  return [collapsed, toggle];
}

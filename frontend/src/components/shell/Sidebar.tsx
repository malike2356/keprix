"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import KeprixLogo from "@/components/shared/KeprixLogo";
import Scrollbar from "@/components/shared/Scrollbar";
import NavIcon from "@/components/ui/NavIcon";
import { fetchPlaybookRuns, interruptedPlaybookCount } from "@/lib/playbook-api";
import type { UiContract } from "@/lib/ui-contract";
import { navigationFromContract, type NavGroupId } from "@/lib/navigation";
import useSWR from "swr";

const DRAWER_WIDTH = 260;

type SidebarProps = {
  mobileOpen: boolean;
  onMobileClose: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  contract?: UiContract | null;
};

export function useWorkspaceSidebarCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    setCollapsed(window.localStorage.getItem("keprix-sidebar-collapsed") === "true");
  }, []);

  const toggle = React.useCallback(() => {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem("keprix-sidebar-collapsed", String(next));
      return next;
    });
  }, []);

  return [collapsed, toggle];
}

function groupItems(group: NavGroupId, items: ReturnType<typeof navigationFromContract>["items"]) {
  return items.filter((item) => item.group === group);
}

export default function Sidebar({ mobileOpen, onMobileClose, contract }: SidebarProps) {
  const pathname = usePathname();
  const { groups, items } = navigationFromContract(contract ?? null);
  const { data: playbookRuns } = useSWR("playbook-runs-nav", () => fetchPlaybookRuns(), {
    refreshInterval: 15_000,
  });
  const interruptedPlaybooks = interruptedPlaybookCount(playbookRuns?.runs ?? []);

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <Box sx={{ flexShrink: 0, px: 2.5, py: 2.5 }}>
        <KeprixLogo size="md" />
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
          Local AI workspace
        </Typography>
      </Box>
      <Divider />
      <Scrollbar sx={{ flex: 1, minHeight: 0, py: 1 }}>
        {groups.map((group) => {
          const groupNav = groupItems(group.id, items);
          if (groupNav.length === 0) return null;
          return (
            <Box key={group.id} sx={{ mb: 1 }}>
              <Typography
                variant="overline"
                sx={{ px: 2.5, py: 1, display: "block", color: "text.secondary" }}
              >
                {group.label}
              </Typography>
              <List dense disablePadding>
                {groupNav.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const badge =
                    item.id === "playbooks" && interruptedPlaybooks > 0 ? interruptedPlaybooks : null;
                  return (
                    <ListItemButton
                      key={item.id}
                      component={NextLink}
                      href={item.href}
                      selected={active}
                      onClick={onMobileClose}
                      sx={{ mx: 1, borderRadius: 1 }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <NavIcon name={item.icon} size={18} />
                      </ListItemIcon>
                      <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2" }} />
                      {badge ? <Chip size="small" color="warning" label={badge} /> : null}
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          );
        })}
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
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH, height: "100vh", overflow: "hidden" },
        }}
      >
        {drawerContent}
      </Drawer>
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            height: "100vh",
            overflow: "hidden",
            borderRight: 1,
            borderColor: "divider",
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>
    </>
  );
}

export { DRAWER_WIDTH };

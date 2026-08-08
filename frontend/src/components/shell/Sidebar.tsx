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
import { IconLayoutSidebarLeftCollapse, IconLayoutSidebarLeftExpand } from "@tabler/icons-react";
import { usePathname } from "next/navigation";
import * as React from "react";
import KeprixLogo from "@/components/shared/KeprixLogo";
import Scrollbar from "@/components/shared/Scrollbar";
import NavIcon from "@/components/ui/NavIcon";
import SidebarNavGroup from "@/components/shell/SidebarNavGroup";
import { useSidebarGroupState } from "@/hooks/useSidebarGroupState";
import { fetchPlaybookRuns, interruptedPlaybookCount } from "@/lib/playbook-api";
import type { UiContract } from "@/lib/ui-contract";
import { isNavHrefActive, navigationFromContract, type NavGroupId } from "@/lib/navigation";
import useSWR from "swr";

const DRAWER_WIDTH = 260;
const DRAWER_WIDTH_COLLAPSED = 72;

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

/** Query string for active-nav matching. Do not patch history.pushState (breaks App Router). */
function useLocationSearch(pathname: string): string {
  const [search, setSearch] = React.useState("");
  React.useEffect(() => {
    const read = () => setSearch(window.location.search.replace(/^\?/, ""));
    read();
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, [pathname]);
  return search;
}

export default function Sidebar({
  mobileOpen,
  onMobileClose,
  collapsed = false,
  onToggleCollapsed,
  contract,
}: SidebarProps) {
  const pathname = usePathname();
  const search = useLocationSearch(pathname);
  const { groups, items } = navigationFromContract(contract ?? null);
  const { isExpanded, toggleGroup } = useSidebarGroupState(groups, items, pathname, search);
  const { data: playbookRuns } = useSWR("playbook-runs-nav", () => fetchPlaybookRuns(), {
    refreshInterval: 15_000,
  });
  const interruptedPlaybooks = interruptedPlaybookCount(playbookRuns?.runs ?? []);
  const rail = Boolean(collapsed);

  const renderNavItem = (item: (typeof items)[number], opts?: { rail?: boolean }) => {
    const active = isNavHrefActive(pathname, search, item.href);
    const badge = item.id === "playbooks" && interruptedPlaybooks > 0 ? interruptedPlaybooks : null;
    const button = (
      <ListItemButton
        key={item.id}
        component="a"
        href={item.href}
        selected={active}
        onClick={() => {
          // Plain <a href>: do not preventDefault. Next soft nav can stick and freeze menus.
          onMobileClose();
        }}
        sx={{
          mx: opts?.rail ? 0.75 : 1,
          borderRadius: 1,
          justifyContent: opts?.rail ? "center" : "flex-start",
          px: opts?.rail ? 1 : undefined,
        }}
      >
        <ListItemIcon sx={{ minWidth: opts?.rail ? 0 : 36, justifyContent: "center" }}>
          <NavIcon name={item.icon} size={18} />
        </ListItemIcon>
        {!opts?.rail ? (
          <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2" }} />
        ) : null}
        {!opts?.rail && badge ? <Chip size="small" color="warning" label={badge} /> : null}
      </ListItemButton>
    );
    if (opts?.rail) {
      return (
        <Tooltip key={item.id} title={item.label} placement="right">
          <Box component="span" sx={{ display: "block" }}>
            {button}
          </Box>
        </Tooltip>
      );
    }
    return button;
  };

  const drawerContent = (opts: { rail: boolean; showCollapseToggle: boolean }) => (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <Box
        sx={{
          flexShrink: 0,
          px: opts.rail ? 1 : 2.5,
          py: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: opts.rail ? "center" : "space-between",
          gap: 1,
        }}
      >
        {!opts.rail ? (
          <Box sx={{ minWidth: 0 }}>
            <KeprixLogo size="md" />
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5 }}>
              Local AI workspace
            </Typography>
          </Box>
        ) : (
          <KeprixLogo variant="icon" size="sm" />
        )}
        {opts.showCollapseToggle && onToggleCollapsed ? (
          <Tooltip title={opts.rail ? "Expand sidebar" : "Collapse sidebar"}>
            <IconButton
              size="small"
              onClick={onToggleCollapsed}
              aria-label={opts.rail ? "Expand sidebar" : "Collapse sidebar"}
            >
              {opts.rail ? (
                <IconLayoutSidebarLeftExpand size={18} stroke={1.75} />
              ) : (
                <IconLayoutSidebarLeftCollapse size={18} stroke={1.75} />
              )}
            </IconButton>
          </Tooltip>
        ) : null}
      </Box>
      <Divider />
      <Scrollbar sx={{ flex: 1, minHeight: 0, py: 1 }}>
        {opts.rail ? (
          <List dense disablePadding>
            {items.map((item) => renderNavItem(item, { rail: true }))}
          </List>
        ) : (
          groups.map((group) => {
            const groupNav = groupItems(group.id, items);
            if (groupNav.length === 0) return null;
            return (
              <SidebarNavGroup
                key={group.id}
                groupId={group.id}
                label={group.label}
                expanded={isExpanded(group.id)}
                onToggle={() => toggleGroup(group.id)}
              >
                <List dense disablePadding>
                  {groupNav.map((item) => renderNavItem(item))}
                </List>
              </SidebarNavGroup>
            );
          })
        )}
      </Scrollbar>
    </Box>
  );

  const paperWidth = rail ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH;

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
        {drawerContent({ rail: false, showCollapseToggle: false })}
      </Drawer>
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          width: paperWidth,
          flexShrink: 0,
          transition: (theme) =>
            theme.transitions.create("width", {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          "& .MuiDrawer-paper": {
            width: paperWidth,
            boxSizing: "border-box",
            height: "100vh",
            overflow: "hidden",
            borderRight: 1,
            borderColor: "divider",
            transition: (theme) =>
              theme.transitions.create("width", {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
          },
        }}
        open
      >
        {drawerContent({ rail: rail, showCollapseToggle: Boolean(onToggleCollapsed) })}
      </Drawer>
    </>
  );
}

export { DRAWER_WIDTH, DRAWER_WIDTH_COLLAPSED };

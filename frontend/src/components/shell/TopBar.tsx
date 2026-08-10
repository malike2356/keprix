"use client";

import AppBar from "@mui/material/AppBar";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import Divider from "@mui/material/Divider";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  IconBell,
  IconLayoutDashboard,
  IconLayoutSidebarRight,
  IconMenu2,
  IconRobot,
  IconSearch,
  IconSettings,
  IconMessages,
  IconUser,
  IconUsers,
  IconCode,
} from "@tabler/icons-react";
import { usePathname } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { useCESession } from "@/lib/ce-auth";
import { fetchUnreadCount } from "@/lib/notifications-api";
import { resolveSettingsNavValue, visibleSettingsNavigation } from "@/lib/settings-navigation";
import type { UiContract } from "@/lib/ui-contract";
import ScoutSafetyIndicator from "@/components/scout/ScoutSafetyIndicator";
import ThemePickerMenu from "@/components/theme/ThemePickerMenu";
import ThemeQuickToggle from "@/components/theme/ThemeQuickToggle";
import NavIcon from "@/components/ui/NavIcon";
import StatusPill from "@/components/ui/StatusPill";
import { normalizeStatusKey } from "@/theme/tokens/status";
import AppSwitcher from "./AppSwitcher";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

type SettingsShortcut = {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; stroke?: number }>;
  adminOnly?: boolean;
};

const SETTINGS_SHORTCUTS: SettingsShortcut[] = [
  { label: "Settings", href: "/settings", icon: IconSettings },
  { label: "Messaging", href: "/settings/messaging", icon: IconMessages },
  { label: "Notifications", href: "/settings/notifications", icon: IconBell },
  { label: "Users", href: "/settings/users", icon: IconUsers, adminOnly: true },
  { label: "Developer", href: "/developer", icon: IconCode, adminOnly: true },
];

type TopBarProps = {
  onMenuClick: () => void;
  onCommandPaletteOpen: () => void;
  onContextToggle: () => void;
  contract: UiContract | null;
};

export default function TopBar({
  onMenuClick,
  onCommandPaletteOpen,
  onContextToggle,
  contract,
}: TopBarProps) {
  const { user, signOut } = useCESession();
  const pathname = usePathname();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const { data: unreadCount = 0, mutate: mutateUnread } = useSWR("notifications-unread", fetchUnreadCount, {
    refreshInterval: 30000,
  });

  const initials = user?.username?.slice(0, 2).toUpperCase() || "KX";
  const agentStatus = normalizeStatusKey(contract?.agent.status || "ready");
  const role = contract?.workspace.role || user?.role || "viewer";
  const isAdmin = role === "admin" || role === "owner";
  const settingsLinks = SETTINGS_SHORTCUTS.filter((item) => !item.adminOnly || isAdmin);
  const settingsNav = visibleSettingsNavigation(isAdmin);
  const showSettingsNav = pathname.startsWith("/settings");
  const activeSettingsNav = resolveSettingsNavValue(pathname, settingsNav);

  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      sx={{
        width: "100%",
        borderBottom: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Toolbar sx={{ gap: 1, flexWrap: "wrap" }}>
        <IconButton
          color="inherit"
          edge="start"
          onClick={onMenuClick}
          sx={{ display: { md: "none" } }}
          aria-label="Open navigation"
        >
          <IconMenu2 size={20} stroke={1.75} />
        </IconButton>

        <Box sx={{ display: { xs: "none", sm: "flex" }, alignItems: "center", gap: 1 }}>
          <WorkspaceSwitcher
            workspaceId={contract?.workspace.id}
            workspaceName={contract?.workspace.name}
          />
          <AppSwitcher />
          {isAdmin ? (
            <Button
              component="a"
              href="/dashboard"
              size="small"
              color="inherit"
              startIcon={<IconLayoutDashboard size={16} stroke={1.75} />}
              sx={{ textTransform: "none", fontWeight: 600 }}
            >
              Dashboard
            </Button>
          ) : null}
        </Box>

        <Tooltip title="Command palette (Ctrl+K)">
          <IconButton color="inherit" onClick={onCommandPaletteOpen} aria-label="Open command palette">
            <IconSearch size={20} stroke={1.75} />
          </IconButton>
        </Tooltip>

        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <IconRobot size={18} stroke={1.75} style={{ color: "var(--kp-text-secondary)" }} />
          <StatusPill status={agentStatus} />
        </Box>

        <ScoutSafetyIndicator />

        <Tooltip title="Notifications">
          <IconButton
            color="inherit"
            size="small"
            aria-label="Notifications"
            component="a"
            href="/notifications"
            onClick={() => {
              void mutateUnread();
            }}
            sx={{ position: "relative" }}
          >
            <IconBell size={18} stroke={1.75} />
            {unreadCount > 0 ? (
              <Box
                component="span"
                sx={{
                  position: "absolute",
                  top: 4,
                  right: 4,
                  minWidth: 16,
                  height: 16,
                  px: 0.5,
                  borderRadius: 8,
                  bgcolor: "error.main",
                  color: "error.contrastText",
                  fontSize: "0.65rem",
                  lineHeight: "16px",
                  textAlign: "center",
                }}
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </Box>
            ) : null}
          </IconButton>
        </Tooltip>

        <Tooltip title="Context panel (Ctrl+Shift+I)">
          <IconButton color="inherit" size="small" onClick={onContextToggle} aria-label="Toggle context panel">
            <IconLayoutSidebarRight size={18} stroke={1.75} />
          </IconButton>
        </Tooltip>

        <ThemeQuickToggle />

        <ThemePickerMenu />

        <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} aria-label="User menu">
          <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: "0.75rem" }}>
            {initials}
          </Avatar>
        </IconButton>

        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
          <Box sx={{ px: 2, py: 1, minWidth: 200 }}>
            <Typography variant="subtitle2">{user?.username || "Guest"}</Typography>
            <Typography variant="caption" color="text.secondary">
              {role}
            </Typography>
          </Box>
          <MenuItem
            component="a"
            href="/settings/account"
            onClick={() => setAnchorEl(null)}
          >
            <ListItemIcon sx={{ minWidth: 32 }}>
              <IconUser size={18} stroke={1.75} />
            </ListItemIcon>
            Account
          </MenuItem>
          {isAdmin ? (
            <MenuItem
              component="a"
              href="/dashboard"
              onClick={() => setAnchorEl(null)}
            >
              <ListItemIcon sx={{ minWidth: 32 }}>
                <IconLayoutDashboard size={18} stroke={1.75} />
              </ListItemIcon>
              Dashboard
            </MenuItem>
          ) : null}
          <Divider />
          {settingsLinks.map((item) => {
            const Icon = item.icon;
            return (
              <MenuItem
                key={item.href}
                component="a"
                href={item.href}
                onClick={() => setAnchorEl(null)}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <Icon size={18} stroke={1.75} />
                </ListItemIcon>
                {item.label}
              </MenuItem>
            );
          })}
          <Divider />
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              signOut();
            }}
          >
            Sign out
          </MenuItem>
        </Menu>
      </Toolbar>
      {showSettingsNav ? (
        <Tabs
          value={activeSettingsNav}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Settings sections"
          sx={{
            minHeight: 42,
            px: { xs: 1, md: 2 },
            borderTop: 1,
            borderColor: "divider",
            "& .MuiTab-root": {
              minHeight: 42,
              textTransform: "none",
              px: 1.5,
            },
          }}
        >
          {settingsNav.map((item) => (
            <Tab
              key={item.href}
              value={item.href}
              label={item.label}
              icon={<NavIcon name={item.icon} size={16} />}
              iconPosition="start"
              component="a"
              href={item.href}
            />
          ))}
        </Tabs>
      ) : null}
    </AppBar>
  );
}

"use client";

import AppBar from "@mui/material/AppBar";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  IconBell,
  IconLayoutSidebarRight,
  IconMenu2,
  IconRobot,
  IconSearch,
} from "@tabler/icons-react";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import { useCESession } from "@/lib/ce-auth";
import { fetchUnreadCount } from "@/lib/notifications-api";
import type { UiContract } from "@/lib/ui-contract";
import ScoutSafetyIndicator from "@/components/scout/ScoutSafetyIndicator";
import ThemePickerMenu from "@/components/theme/ThemePickerMenu";
import ThemeQuickToggle from "@/components/theme/ThemeQuickToggle";
import StatusPill from "@/components/ui/StatusPill";
import { normalizeStatusKey } from "@/theme/tokens/status";
import AppSwitcher from "./AppSwitcher";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

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
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const { data: unreadCount = 0, mutate: mutateUnread } = useSWR("notifications-unread", fetchUnreadCount, {
    refreshInterval: 30000,
  });

  const initials = user?.username?.slice(0, 2).toUpperCase() || "KX";
  const agentStatus = normalizeStatusKey(contract?.agent.status || "ready");

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
        </Box>

        <Tooltip title="Command palette (Ctrl+K)">
          <IconButton color="inherit" onClick={onCommandPaletteOpen} aria-label="Open command palette">
            <IconSearch size={20} stroke={1.75} />
          </IconButton>
        </Tooltip>

        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <IconRobot size={18} stroke={1.75} style={{ opacity: 0.7 }} />
          <StatusPill status={agentStatus} />
        </Box>

        <ScoutSafetyIndicator />

        <Tooltip title="Notifications">
          <IconButton
            color="inherit"
            size="small"
            aria-label="Notifications"
            component={Link}
            href="/notifications"
            onClick={() => void mutateUnread()}
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
          <Box sx={{ px: 2, py: 1, minWidth: 180 }}>
            <Typography variant="subtitle2">{user?.username || "Guest"}</Typography>
            <Typography variant="caption" color="text.secondary">
              {contract?.workspace.role || user?.role || "viewer"}
            </Typography>
          </Box>
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
    </AppBar>
  );
}

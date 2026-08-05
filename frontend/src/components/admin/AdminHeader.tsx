"use client";

import AppBar from "@mui/material/AppBar";
import Avatar from "@mui/material/Avatar";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { IconBell, IconMenu2, IconSearch } from "@tabler/icons-react";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import ScoutSafetyIndicator from "@/components/scout/ScoutSafetyIndicator";
import ThemePickerMenu from "@/components/theme/ThemePickerMenu";
import { useCESession } from "@/lib/ce-auth";
import { fetchPendingMutationCount } from "@/lib/admin-dashboard-api";

type AdminHeaderProps = {
  collapsed: boolean;
  onMenuClick: () => void;
  onCommandPaletteOpen?: () => void;
  pendingMutations?: number;
};

function titleFromPath(pathname: string): string {
  const segment = pathname.split("/").filter(Boolean).pop() || "overview";
  return segment.charAt(0).toUpperCase() + segment.slice(1);
}

export function AdminHeader({ onMenuClick, onCommandPaletteOpen }: AdminHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useCESession();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [pendingCount, setPendingCount] = React.useState(0);

  React.useEffect(() => {
    fetchPendingMutationCount()
      .then(setPendingCount)
      .catch(() => setPendingCount(0));
  }, []);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "/" && !event.ctrlKey && !event.metaKey) {
        const target = event.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
          return;
        }
        event.preventDefault();
        onCommandPaletteOpen?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCommandPaletteOpen]);

  const initials = user?.username?.slice(0, 2).toUpperCase() || "KX";

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
      <Toolbar sx={{ gap: 1 }}>
        <IconButton edge="start" onClick={onMenuClick} sx={{ display: { md: "none" } }} aria-label="Open navigation">
          <IconMenu2 size={20} stroke={1.75} />
        </IconButton>

        <Breadcrumbs aria-label="breadcrumb" sx={{ display: { xs: "none", sm: "flex" } }}>
          <Link component={NextLink} underline="hover" color="inherit" href="/dashboard">
            Admin console
          </Link>
          <Typography color="text.primary">{titleFromPath(pathname)}</Typography>
        </Breadcrumbs>

        <Button
          component={NextLink}
          href="/home"
          size="small"
          variant="text"
          sx={{ display: { xs: "none", md: "inline-flex" }, ml: 1, flexShrink: 0 }}
        >
          Workspace home
        </Button>

        <Box sx={{ flexGrow: 1 }} />

        <Tooltip title="Search (/)">
          <IconButton color="inherit" onClick={onCommandPaletteOpen} aria-label="Open search">
            <IconSearch size={20} stroke={1.75} />
          </IconButton>
        </Tooltip>

        <Tooltip title="Pending mutations">
          <IconButton
            color="inherit"
            component={NextLink}
            href="/admin/mutations"
            aria-label="Notifications"
          >
            <Badge badgeContent={pendingCount || 0} color="warning">
              <IconBell size={20} stroke={1.75} />
            </Badge>
          </IconButton>
        </Tooltip>

        <ScoutSafetyIndicator />

        <ThemePickerMenu />

        <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} aria-label="User menu">
          <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: "0.75rem" }}>
            {initials}
          </Avatar>
        </IconButton>

        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
          <Box sx={{ px: 2, py: 1, minWidth: 200 }}>
            <Typography variant="subtitle2">{user?.username || "Admin"}</Typography>
            <Typography variant="caption" color="text.secondary">
              {user?.role || "admin"}
            </Typography>
          </Box>
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              router.push("/home");
            }}
          >
            Workspace home
          </MenuItem>
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              router.push("/admin/settings");
            }}
          >
            Settings
          </MenuItem>
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

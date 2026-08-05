"use client";

import MenuIcon from "@mui/icons-material/Menu";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import SessionList from "@/components/chat/SessionList";
import WorkspaceHeader from "@/components/workspace/WorkspaceHeader";

type ChatWorkspaceShellProps = {
  children: React.ReactNode;
  sessionId?: string;
  sessionTitle?: string;
};

const SIDEBAR_WIDTH = 280;

export default function ChatWorkspaceShell({ children, sessionId, sessionTitle }: ChatWorkspaceShellProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"), { noSsr: true });
  const [drawerOpen, setDrawerOpen] = React.useState(false);

  const sidebar = (
    <Box sx={{ width: SIDEBAR_WIDTH, height: "100%", bgcolor: "background.paper", borderRight: 1, borderColor: "divider" }}>
      <SessionList onNavigate={() => setDrawerOpen(false)} />
    </Box>
  );

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {isMobile ? (
        <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} ModalProps={{ keepMounted: true }}>
          {sidebar}
        </Drawer>
      ) : (
        sidebar
      )}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center" }}>
          {isMobile ? (
            <IconButton onClick={() => setDrawerOpen(true)} aria-label="Open sessions" sx={{ ml: 1 }}>
              <MenuIcon />
            </IconButton>
          ) : null}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <WorkspaceHeader sessionId={sessionId} title={sessionTitle} />
          </Box>
        </Box>
        <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>{children}</Box>
      </Box>
    </Box>
  );
}

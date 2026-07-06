"use client";

import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { SkeletonText } from "@/components/ui/loading";
import { fetchUiContract, type UiContract } from "@/lib/ui-contract";
import CommandPalette from "./CommandPalette";
import ContextPanel from "./ContextPanel";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import WorkspaceFooter from "./WorkspaceFooter";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const [contextOpen, setContextOpen] = React.useState(false);
  const [contract, setContract] = React.useState<UiContract | null>(null);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "i") {
        event.preventDefault();
        setContextOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  React.useEffect(() => {
    fetchUiContract()
      .then(setContract)
      .catch(() => setContract(null));
  }, []);

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} contract={contract} />
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          overflow: "hidden",
        }}
      >
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          onCommandPaletteOpen={() => setPaletteOpen(true)}
          onContextToggle={() => setContextOpen((open) => !open)}
          contract={contract}
        />
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} contract={contract} />
        <Box sx={{ display: "flex", flex: 1, flexDirection: "column", minHeight: 0 }}>
          <Box sx={{ display: "flex", flex: 1, minHeight: 0 }}>
            <Box
              component="main"
              sx={{
                flex: 1,
                p: { xs: 2, sm: 3 },
                minWidth: 0,
                overflow: "auto",
              }}
            >
              <Toolbar sx={{ display: { xs: "block", md: "none" }, minHeight: 0 }} />
              <Box sx={{ width: "100%" }}>{children}</Box>
            </Box>
            <ContextPanel
              open={contextOpen}
              onClose={() => setContextOpen(false)}
              title="Agent context"
            >
              {contract ? (
                <Box sx={{ display: "grid", gap: 1.5 }}>
                  <Typography variant="body2">
                    <strong>Agent:</strong> {contract.agent.label}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Workspace:</strong> {contract.workspace.name}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Role:</strong> {contract.workspace.role}
                  </Typography>
                  {contract.agent.current_job && (
                    <Typography variant="body2">
                      <strong>Current job:</strong> {contract.agent.current_job}
                    </Typography>
                  )}
                  {contract.agent.awaiting_approval && (
                    <Typography variant="body2" color="warning.main">
                      Awaiting approval
                    </Typography>
                  )}
                </Box>
              ) : (
                <SkeletonText lines={2} />
              )}
            </ContextPanel>
          </Box>
          <WorkspaceFooter />
        </Box>
      </Box>
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import dynamic from "next/dynamic";
import * as React from "react";
import { SkeletonText } from "@/components/ui/loading";
import OnboardingBanner from "@/components/agent-os/OnboardingBanner";
import UpgradeBanner from "@/components/upgrade/UpgradeBanner";
import { fetchUiContract, getCachedUiContract, type UiContract } from "@/lib/ui-contract";
import ContextPanel from "./ContextPanel";
import MobileBottomNav from "./MobileBottomNav";
import Sidebar, { useWorkspaceSidebarCollapsed } from "./Sidebar";
import TopBar from "./TopBar";
import WorkspaceFooter from "./WorkspaceFooter";
import { OperatorCopilotFab, useOperatorAttentionBadge } from "@/components/operator/OperatorCopilotDrawer";

const CommandPalette = dynamic(() => import("./CommandPalette"), { ssr: false });
const OperatorCopilotDrawer = dynamic(
  () => import("@/components/operator/OperatorCopilotDrawer").then((mod) => mod.default),
  { ssr: false },
);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [collapsed, toggleCollapsed] = useWorkspaceSidebarCollapsed();
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const [contextOpen, setContextOpen] = React.useState(false);
  const [copilotOpen, setCopilotOpen] = React.useState(false);
  const [contract, setContract] = React.useState<UiContract | null>(null);
  const operatorBadge = useOperatorAttentionBadge();

  React.useEffect(() => {
    const cached = getCachedUiContract();
    if (cached) {
      setContract(cached);
    }
    fetchUiContract()
      .then(setContract)
      .catch(() => undefined);
  }, []);

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

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        contract={contract}
      />
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
                pb: { xs: 9, md: 3 },
                minWidth: 0,
                overflow: "auto",
              }}
            >
              <Toolbar sx={{ display: { xs: "block", md: "none" }, minHeight: 0 }} />
              <Box sx={{ width: "100%" }}>
                <OnboardingBanner />
                <UpgradeBanner />
                {children}
              </Box>
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
      <OperatorCopilotFab onClick={() => setCopilotOpen(true)} badge={operatorBadge} />
      <OperatorCopilotDrawer open={copilotOpen} onClose={() => setCopilotOpen(false)} />
      <MobileBottomNav />
    </Box>
  );
}

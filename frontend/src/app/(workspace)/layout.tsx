"use client";

import Box from "@mui/material/Box";
import { usePathname } from "next/navigation";
import AppShell from "@/components/shell/AppShell";
import CommandPalette from "@/components/shared/CommandPalette";
import ChatWorkspaceShell from "@/components/workspace/ChatWorkspaceShell";
import { useCommandPalette } from "@/hooks/useCommandPalette";
import { SessionProvider, useRequireSession } from "@/lib/ce-auth";
import { WorkspaceThemeRestore } from "@/components/providers/WorkspaceThemeRestore";

function WorkspaceLayoutInner({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const pathname = usePathname();
  const { open, closePalette } = useCommandPalette();
  const isChatRoute = pathname?.startsWith("/chat");

  if (isChatRoute) {
    return (
      <Box sx={{ minHeight: "100vh" }}>
        <CommandPalette open={open} onClose={closePalette} />
        {pathname === "/chat" ? <ChatWorkspaceShell>{children}</ChatWorkspaceShell> : children}
      </Box>
    );
  }

  return (
    <>
      <AppShell>{children}</AppShell>
      <CommandPalette open={open} onClose={closePalette} />
    </>
  );
}

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <WorkspaceThemeRestore />
      <WorkspaceLayoutInner>{children}</WorkspaceLayoutInner>
    </SessionProvider>
  );
}

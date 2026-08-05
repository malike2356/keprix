"use client";

import Box from "@mui/material/Box";
import * as React from "react";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import AppShell from "@/components/shell/AppShell";
import ChatWorkspaceShell from "@/components/workspace/ChatWorkspaceShell";
import { SessionProvider, useRequireSession } from "@/lib/ce-auth";
import { WorkspaceThemeRestore } from "@/components/providers/WorkspaceThemeRestore";
import { simplifiedModeGuard } from "@/lib/simplifiedMode";

function WorkspaceLayoutInner({ children }: { children: React.ReactNode }) {
  useRequireSession();
  const pathname = usePathname();
  const router = useRouter();
  const isChatRoute = pathname?.startsWith("/chat");

  React.useEffect(() => {
    if (!pathname || pathname === "/agent-os") return;
    simplifiedModeGuard(pathname)
      .then((result) => {
        if (result.blocked && result.redirect) router.replace(`${result.redirect}?simplified_redirect=1`);
      })
      .catch(() => undefined);
  }, [pathname, router]);

  if (isChatRoute) {
    return (
      <Box sx={{ minHeight: "100vh" }}>
        {pathname === "/chat" ? (
          <ChatWorkspaceShell>
            <React.Suspense>{children}</React.Suspense>
          </ChatWorkspaceShell>
        ) : (
          <React.Suspense>{children}</React.Suspense>
        )}
      </Box>
    );
  }

  return (
    <AppShell>
      <React.Suspense>{children}</React.Suspense>
    </AppShell>
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

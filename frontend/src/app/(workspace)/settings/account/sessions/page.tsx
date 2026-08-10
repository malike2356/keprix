"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import * as React from "react";
import PageHeader from "@/components/ui/PageHeader";
import { SessionManagementPanel } from "@/components/sessions/session-ui";
import {
  fetchActiveSessions,
  revokeActiveSession,
  revokeEverywhere,
} from "@/lib/account-api";

export default function AccountSessionsPage() {
  const [banner, setBanner] = React.useState<string | null>(null);
  React.useEffect(() => {
    const stored = window.sessionStorage.getItem("keprix.newLoginBanner");
    if (stored) setBanner(stored);
  }, []);

  const api = React.useMemo(
    () => ({
      list: async () => {
        const rows = await fetchActiveSessions();
        const stored = window.sessionStorage.getItem("keprix.newLoginBanner");
        if (stored) setBanner(stored);
        return rows.map((row) => ({
          sessionId: row.session_id,
          deviceLabel: row.device_label,
          ipMasked: row.ip_address_masked ?? null,
          lastActiveAt: row.last_seen_at ? new Date(row.last_seen_at * 1000).toISOString() : null,
          createdAt: row.created_at ? new Date(row.created_at * 1000).toISOString() : null,
          isCurrent: Boolean(row.is_current),
        }));
      },
      revokeOne: (sessionId: string) => revokeActiveSession(sessionId),
      revokeAll: async () => {
        await revokeEverywhere();
        window.location.href = "/login";
      },
    }),
    [],
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <PageHeader
        title="Sessions"
        description="Devices and browsers currently signed in to your account."
      />
      <SessionManagementPanel
        api={api}
        newLoginBanner={banner}
        onDismissBanner={() => {
          window.sessionStorage.removeItem("keprix.newLoginBanner");
          setBanner(null);
        }}
        title="Where you're logged in"
      />
      <Button component="a" href="/settings/account" variant="outlined">
        Back to account
      </Button>
    </Box>
  );
}

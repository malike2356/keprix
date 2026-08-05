"use client";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import * as React from "react";
import SecurityOverviewCard from "@/components/account/SecurityOverviewCard";
import { fetchAccountProfile, fetchSsoLinks, fetchActiveSessions } from "@/lib/account-api";

export default function AccountOverviewPage() {
  const [totpEnabled, setTotpEnabled] = React.useState(false);
  const [ssoCount, setSsoCount] = React.useState(0);
  const [sessionCount, setSessionCount] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([fetchAccountProfile(), fetchSsoLinks(), fetchActiveSessions()])
      .then(([profile, links, sessions]) => {
        setTotpEnabled(Boolean(profile.totp_enabled));
        setSsoCount(links.length);
        setSessionCount(sessions.length);
      })
      .catch(() => {
        setTotpEnabled(false);
        setSsoCount(0);
        setSessionCount(0);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Typography variant="h6">Account and security</Typography>
      <Typography color="text.secondary">
        Manage your profile, sign-in methods, two-factor authentication, and active sessions.
      </Typography>
      {loading ? (
        <Typography color="text.secondary">Loading security overview...</Typography>
      ) : (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <SecurityOverviewCard
              title="Profile"
              description="Update your display name, email, and preferences."
              href="/settings/account/profile"
              statusLabel="Open"
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <SecurityOverviewCard
              title="Two-factor authentication"
              description="Protect sign-in with an authenticator app."
              href="/settings/account/two-factor"
              statusLabel={totpEnabled ? "Enabled" : "Off"}
              statusColor={totpEnabled ? "success" : "warning"}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <SecurityOverviewCard
              title="Connected accounts"
              description="Link Google, GitHub, or OpenID Connect sign-in."
              href="/settings/account/connected-accounts"
              statusLabel={ssoCount === 0 ? "None linked" : `${ssoCount} linked`}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <SecurityOverviewCard
              title="Active sessions"
              description="Review devices signed in to this account."
              href="/settings/account/sessions"
              statusLabel={sessionCount === 1 ? "1 device" : `${sessionCount} devices`}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <SecurityOverviewCard
              title="Password"
              description="Change your password or recover access."
              href="/settings/account/password"
              statusLabel="Manage"
            />
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

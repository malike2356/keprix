"use client";

import Box from "@mui/material/Box";
import PageHeader from "@/components/ui/PageHeader";
import TwoFactorSetupPanel from "@/components/auth/TwoFactorSetupPanel";

export default function AccountTwoFactorPage() {
  return (
    <Box>
      <PageHeader
        title="Two-factor authentication"
        description="Protect your account with an authenticator app and backup recovery codes."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Account", href: "/settings/account/profile" },
          { label: "Two-factor" },
        ]}
      />
      <TwoFactorSetupPanel />
    </Box>
  );
}

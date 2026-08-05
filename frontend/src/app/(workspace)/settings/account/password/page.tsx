"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import PageHeader from "@/components/ui/PageHeader";
import ChangePasswordForm from "@/components/auth/ChangePasswordForm";

export default function AccountPasswordPage() {
  return (
    <Box>
      <PageHeader
        title="Password"
        description="Change your account password."
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Account", href: "/settings/account/profile" },
          { label: "Password" },
        ]}
      />
      <Card variant="outlined">
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>
    </Box>
  );
}

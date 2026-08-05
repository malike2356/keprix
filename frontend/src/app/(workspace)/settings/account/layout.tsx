"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import AccountNav from "@/components/account/AccountNav";

export default function AccountSettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 1 }}>
        Account and security
      </Typography>
      <AccountNav />
      {children}
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import KeprixLogo from "@/components/shared/KeprixLogo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ minHeight: "100vh", display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: KEPRIX_COLORS.bgDefault,
          color: KEPRIX_COLORS.textPrimary,
          p: 4,
        }}
      >
        <KeprixLogo size="lg" onDark />
        <Typography variant="h6" sx={{ mt: 3, textAlign: "center", maxWidth: 360 }}>
          Your self-hosted AI agent. Running on your terms.
        </Typography>
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", p: 3, bgcolor: "background.default" }}>
        <Card sx={{ width: "100%", maxWidth: 440 }}>
          <CardContent sx={{ p: 4 }}>{children}</CardContent>
        </Card>
      </Box>
    </Box>
  );
}

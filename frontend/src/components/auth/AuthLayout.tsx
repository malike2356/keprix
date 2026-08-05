"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { KEPRIX_COLORS } from "@/theme/keprix-theme";
import KeprixLogo from "@/components/shared/KeprixLogo";
import KeprixWatermark from "@/components/shared/KeprixWatermark";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ minHeight: "100vh", display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
      <Box
        sx={{
          position: "relative",
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: KEPRIX_COLORS.bgDefault,
          color: KEPRIX_COLORS.textPrimary,
          p: 4,
          overflow: "hidden",
        }}
      >
        <KeprixWatermark opacity={0.09} size="min(80vmin, 560px)" />
        <Box sx={{ position: "relative", zIndex: 1, textAlign: "center" }}>
          <KeprixLogo size="lg" onDark />
          <Typography variant="h6" sx={{ mt: 3, textAlign: "center", maxWidth: 360 }}>
            Your self-hosted AI agent. Running on your terms.
          </Typography>
        </Box>
      </Box>
      <Box
        sx={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 3,
          bgcolor: "background.default",
          overflow: "hidden",
        }}
      >
        <KeprixWatermark
          opacity={0.05}
          size="min(90vmin, 420px)"
          sx={{ display: { xs: "block", md: "none" } }}
        />
        <Card sx={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 440 }}>
          <CardContent sx={{ p: 4 }}>{children}</CardContent>
        </Card>
      </Box>
    </Box>
  );
}

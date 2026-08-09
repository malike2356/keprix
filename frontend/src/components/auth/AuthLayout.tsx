"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import KeprixLogo from "@/components/shared/KeprixLogo";
import KeprixWatermark from "@/components/shared/KeprixWatermark";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  const onDark = theme.palette.mode === "dark";

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
      <Box
        sx={{
          position: "relative",
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "background.default",
          color: "text.primary",
          borderRight: 1,
          borderColor: "divider",
          p: 4,
          overflow: "hidden",
        }}
      >
        <KeprixWatermark opacity={0.09} size="min(80vmin, 560px)" />
        <Box sx={{ position: "relative", zIndex: 1, textAlign: "center" }}>
          <KeprixLogo size="lg" onDark={onDark} />
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
          bgcolor: "background.paper",
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

"use client";

import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Link from "next/link";

export default function GraphEmptyState() {
  return (
    <Box
      sx={{
        height: "100%",
        display: "grid",
        placeItems: "center",
        textAlign: "center",
        px: 3,
        bgcolor: "transparent",
      }}
    >
      <Box sx={{ maxWidth: 420 }}>
        <AccountTreeOutlinedIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1.5 }} />
          <Typography variant="h6" sx={{ fontWeight: 600, letterSpacing: -0.2 }}>
            No connections yet
          </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2.5, lineHeight: 1.55 }}>
          Save memories, chat, or add Temporal entities. The graph fills in quietly as your workspace grows.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} justifyContent="center">
          <Button component={Link} href="/memory" variant="contained" disableElevation>
            Open Memory
          </Button>
          <Button component={Link} href="/memory/galaxy" variant="outlined" color="inherit" sx={{ borderColor: "divider" }}>
            Galaxy
          </Button>
          <Button component={Link} href="/chat" color="inherit">
            Chat
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

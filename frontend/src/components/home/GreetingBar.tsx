"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { IconPlus } from "@tabler/icons-react";
import NextLink from "next/link";
import { getCEUser } from "@/lib/ce-api";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 18) return "Good afternoon";
  if (hour >= 18 && hour < 22) return "Good evening";
  return "Working late";
}

export default function GreetingBar() {
  const user = getCEUser();
  const firstName = (user?.display_name ?? user?.username ?? "").split(" ")[0] || "there";

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        mb: 4,
        gap: 2,
      }}
    >
      <Box>
        <Typography variant="h4" fontWeight={600} gutterBottom={false}>
          {getGreeting()}, {firstName}.
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Your agent is ready.
        </Typography>
      </Box>
      <Button
        component={NextLink}
        href="/chat"
        variant="contained"
        size="medium"
        startIcon={<IconPlus size={16} stroke={2} />}
        sx={{ flexShrink: 0 }}
      >
        New session
      </Button>
    </Box>
  );
}

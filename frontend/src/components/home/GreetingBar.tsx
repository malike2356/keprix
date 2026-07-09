"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import { IconPlus } from "@tabler/icons-react";
import NextLink from "next/link";
import { useCESession } from "@/lib/ce-auth";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 18) return "Good afternoon";
  if (hour >= 18 && hour < 22) return "Good evening";
  return "Working late";
}

function displayFirstName(user: { display_name?: string | null; username?: string | null }): string {
  const raw = (user.display_name ?? user.username ?? "").trim();
  if (!raw) return "there";
  if (raw.includes("@")) return raw.split("@")[0] || "there";
  return raw.split(" ")[0] || "there";
}

export default function GreetingBar() {
  const { user } = useCESession();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Match SSR and first client paint; personalize only after mount.
  const greeting = mounted ? getGreeting() : "Hello";
  const firstName = mounted && user ? displayFirstName(user) : "there";

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
          {greeting}, {firstName}.
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

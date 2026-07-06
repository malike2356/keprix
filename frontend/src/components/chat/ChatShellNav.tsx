"use client";

import AppsOutlinedIcon from "@mui/icons-material/AppsOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import NextLink from "next/link";
import { useCESession } from "@/lib/ce-auth";

type ChatShellNavProps = {
  variant?: "inline" | "footer";
};

export default function ChatShellNav({ variant = "inline" }: ChatShellNavProps) {
  const { user } = useCESession();
  const isOwner = user?.role === "admin" || user?.role === "owner";

  if (variant === "footer") {
    return (
      <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap" }}>
        <Button component={NextLink} href="/launcher" size="small" variant="text">
          Home
        </Button>
        {isOwner ? (
          <Button component={NextLink} href="/dashboard" size="small" variant="text">
            Dashboard
          </Button>
        ) : null}
      </Stack>
    );
  }

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexShrink: 0 }}>
      <Button
        component={NextLink}
        href="/launcher"
        size="small"
        color="inherit"
        startIcon={<AppsOutlinedIcon fontSize="small" />}
        sx={{ textTransform: "none", fontWeight: 600, minWidth: 0, px: 1 }}
      >
        Home
      </Button>
      {isOwner ? (
        <Button
          component={NextLink}
          href="/dashboard"
          size="small"
          color="inherit"
          startIcon={<DashboardOutlinedIcon fontSize="small" />}
          sx={{ textTransform: "none", fontWeight: 600, minWidth: 0, px: 1 }}
        >
          Dashboard
        </Button>
      ) : null}
    </Stack>
  );
}

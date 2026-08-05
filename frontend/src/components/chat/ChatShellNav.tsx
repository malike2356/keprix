"use client";

import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
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
        <Button component={NextLink} href="/home" size="small" variant="text">
          Workspace
        </Button>
        <Button
          component={NextLink}
          href="/files"
          size="small"
          variant="text"
          startIcon={<FolderOutlinedIcon fontSize="small" />}
        >
          Files
        </Button>
        {isOwner ? (
          <Button component={NextLink} href="/dashboard" size="small" variant="text">
            Admin console
          </Button>
        ) : null}
      </Stack>
    );
  }

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexShrink: 0 }}>
      <Button
        component={NextLink}
        href="/home"
        size="small"
        color="inherit"
        startIcon={<HomeOutlinedIcon fontSize="small" />}
        sx={{ textTransform: "none", fontWeight: 600, minWidth: 0, px: 1 }}
      >
        Workspace
      </Button>
      <Button
        component={NextLink}
        href="/files"
        size="small"
        color="inherit"
        startIcon={<FolderOutlinedIcon fontSize="small" />}
        sx={{ textTransform: "none", fontWeight: 600, minWidth: 0, px: 1 }}
      >
        Files
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
          Admin console
        </Button>
      ) : null}
    </Stack>
  );
}

"use client";

import Button from "@mui/material/Button";
import AppsOutlinedIcon from "@mui/icons-material/AppsOutlined";
import NextLink from "next/link";

export default function AppSwitcher() {
  return (
    <Button
      component={NextLink}
      href="/launcher"
      size="small"
      color="inherit"
      startIcon={<AppsOutlinedIcon />}
      sx={{ textTransform: "none", fontWeight: 600 }}
    >
      Apps
    </Button>
  );
}

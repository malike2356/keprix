"use client";

import Button from "@mui/material/Button";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";

export default function AppSwitcher() {
  return (
    <Button
      component="a"
      href="/home"
      size="small"
      color="inherit"
      startIcon={<HomeOutlinedIcon />}
      sx={{ textTransform: "none", fontWeight: 600 }}
    >
      Workspace home
    </Button>
  );
}

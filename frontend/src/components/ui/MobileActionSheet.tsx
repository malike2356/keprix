"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

type MobileActionSheetProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children?: ReactNode;
  primaryAction?: { label: string; onClick: () => void; disabled?: boolean };
  secondaryAction?: { label: string; onClick: () => void };
};

export default function MobileActionSheet({
  open,
  title,
  onClose,
  children,
  primaryAction,
  secondaryAction,
}: MobileActionSheetProps) {
  return (
    <Drawer anchor="bottom" open={open} onClose={onClose} PaperProps={{ sx: { borderTopLeftRadius: 12, borderTopRightRadius: 12 } }}>
      <Box sx={{ p: 2, display: "grid", gap: 2 }}>
        <Typography variant="subtitle1" fontWeight={600}>{title}</Typography>
        {children}
        <Box sx={{ display: "grid", gap: 1 }}>
          {primaryAction ? (
            <Button variant="contained" disabled={primaryAction.disabled} onClick={primaryAction.onClick}>
              {primaryAction.label}
            </Button>
          ) : null}
          {secondaryAction ? (
            <Button variant="outlined" color="inherit" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          ) : null}
        </Box>
      </Box>
    </Drawer>
  );
}

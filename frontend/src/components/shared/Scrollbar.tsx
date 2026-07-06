"use client";

import Box from "@mui/material/Box";
import { styled, useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import type { SxProps, Theme } from "@mui/material/styles";
import SimpleBar from "simplebar-react";
import "simplebar-react/dist/simplebar.min.css";
import type { ReactNode } from "react";

const SimpleBarStyle = styled(SimpleBar)(() => ({
  height: "100%",
  maxHeight: "100%",
}));

type ScrollbarProps = {
  children: ReactNode;
  sx?: SxProps<Theme>;
};

export default function Scrollbar({ children, sx }: ScrollbarProps) {
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("lg"));

  if (compact) {
    return <Box sx={{ overflowX: "auto", ...sx }}>{children}</Box>;
  }

  return <SimpleBarStyle sx={sx}>{children}</SimpleBarStyle>;
}

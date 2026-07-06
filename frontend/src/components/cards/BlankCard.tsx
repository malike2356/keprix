"use client";

import Card from "@mui/material/Card";
import type { SxProps, Theme } from "@mui/material/styles";
import type { ReactNode } from "react";

type BlankCardProps = {
  children: ReactNode;
  className?: string;
  sx?: SxProps<Theme>;
};

export default function BlankCard({ children, className, sx }: BlankCardProps) {
  return (
    <Card className={className} variant="outlined" sx={{ p: 0, position: "relative", ...sx }}>
      {children}
    </Card>
  );
}

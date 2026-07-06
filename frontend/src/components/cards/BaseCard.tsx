"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

type BaseCardProps = {
  title: string;
  chipTitle?: string;
  children: ReactNode;
};

export default function BaseCard({ title, chipTitle, children }: BaseCardProps) {
  return (
    <Card variant="outlined" sx={{ p: 0, width: "100%" }}>
      <Box sx={{ p: 2, display: "flex", alignItems: "center" }}>
        <Typography variant="h6" fontWeight={600}>
          {title}
        </Typography>
        {chipTitle ? <Chip label={chipTitle} size="small" sx={{ ml: "auto", fontWeight: 500 }} /> : null}
      </Box>
      <Divider />
      <CardContent>{children}</CardContent>
    </Card>
  );
}

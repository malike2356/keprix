"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonBlock } from "@/components/ui/loading";

type StatCardProps = {
  title: string;
  value: string | number;
  delta?: string;
  positive?: boolean;
  icon: ReactNode;
  color?: "primary" | "secondary" | "success" | "warning" | "error" | "info";
  loading?: boolean;
  href?: string;
};

const badgeColors = {
  primary: "primary.main",
  secondary: "secondary.main",
  success: "success.main",
  warning: "warning.main",
  error: "error.main",
  info: "info.main",
} as const;

export default function StatCard({
  title,
  value,
  delta,
  positive = true,
  icon,
  color = "primary",
  loading = false,
  href,
}: StatCardProps) {
  if (loading) {
    return (
      <DashboardCard>
        <SkeletonBlock height={120} />
      </DashboardCard>
    );
  }

  const body = (
    <DashboardCard>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {title}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            {value}
          </Typography>
          {delta ? (
            <Typography variant="caption" color={positive ? "success.main" : "error.main"} fontWeight={600} sx={{ mt: 0.75, display: "block" }}>
              {delta}
            </Typography>
          ) : null}
        </Box>
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: 1,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            bgcolor: `${badgeColors[color]}22`,
            color: badgeColors[color],
          }}
        >
          {icon}
        </Box>
      </Box>
    </DashboardCard>
  );

  if (href) {
    return (
      <Box
        component="a"
        href={href}
        sx={{ textDecoration: "none", color: "inherit", display: "block" }}
      >
        {body}
      </Box>
    );
  }

  return body;
}

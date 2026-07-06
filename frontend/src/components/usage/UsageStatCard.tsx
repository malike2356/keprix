"use client";

import type { ReactNode } from "react";
import StatCard from "@/components/admin/StatCard";

type UsageStatCardProps = {
  title: string;
  value: string | number;
  icon: ReactNode;
  color?: "primary" | "secondary" | "success" | "warning" | "error" | "info";
  loading?: boolean;
};

export default function UsageStatCard({
  title,
  value,
  icon,
  color = "primary",
  loading = false,
}: UsageStatCardProps) {
  return (
    <StatCard
      title={title}
      value={value}
      icon={icon}
      color={color}
      loading={loading}
    />
  );
}

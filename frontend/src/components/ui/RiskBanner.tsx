"use client";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";

type RiskBannerProps = {
  level: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
};

const severityMap = {
  low: "info",
  medium: "warning",
  high: "warning",
  critical: "error",
} as const;

export default function RiskBanner({ level, title, message }: RiskBannerProps) {
  return (
    <Alert severity={severityMap[level]} sx={{ mb: 2 }}>
      <AlertTitle>
        {title} ({level})
      </AlertTitle>
      {message}
    </Alert>
  );
}

"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

type DashboardCardProps = {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  footer?: ReactNode;
  cardHeading?: boolean;
  headTitle?: ReactNode;
  headSubtitle?: ReactNode;
  middleContent?: ReactNode;
  children?: ReactNode;
};

export default function DashboardCard({
  title,
  subtitle,
  children,
  action,
  footer,
  cardHeading = false,
  headTitle,
  headSubtitle,
  middleContent,
}: DashboardCardProps) {
  return (
    <Card variant="outlined" sx={{ p: 0, height: "100%" }}>
      {cardHeading ? (
        <CardContent>
          <Typography variant="h5">{headTitle}</Typography>
          {headSubtitle ? (
            <Typography variant="body2" color="text.secondary">
              {headSubtitle}
            </Typography>
          ) : null}
        </CardContent>
      ) : (
        <CardContent sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column" }}>
          {title ? (
            <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {title}
                </Typography>
                {subtitle ? (
                  <Typography variant="body2" color="text.secondary">
                    {subtitle}
                  </Typography>
                ) : null}
              </Box>
              {action}
            </Stack>
          ) : null}
          <Box sx={{ flex: 1, minHeight: 0 }}>{children}</Box>
        </CardContent>
      )}
      {middleContent}
      {footer}
    </Card>
  );
}

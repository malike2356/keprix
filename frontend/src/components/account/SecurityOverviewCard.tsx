"use client";

import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";

type SecurityOverviewCardProps = {
  title: string;
  description: string;
  href: string;
  statusLabel: string;
  statusColor?: "default" | "success" | "warning" | "error";
};

export default function SecurityOverviewCard({
  title,
  description,
  href,
  statusLabel,
  statusColor = "default",
}: SecurityOverviewCardProps) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardActionArea component={NextLink} href={href} sx={{ height: "100%" }}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
            <Typography variant="subtitle1">{title}</Typography>
            <Chip size="small" label={statusLabel} color={statusColor} variant="outlined" />
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {description}
          </Typography>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

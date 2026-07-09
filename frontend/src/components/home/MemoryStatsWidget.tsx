"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import useSWR from "swr";
import { fetchHomeBrainStats, type HomeBrainStats } from "@/lib/home-api";

function StatRow({ label, value, href, loading }: {
  label: string;
  value: number;
  href: string;
  loading: boolean;
}) {
  return (
    <CardActionArea component={NextLink} href={href}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 2, py: 1.25 }}>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        {loading ? (
          <Skeleton variant="text" width={32} />
        ) : (
          <Typography variant="body2" fontWeight={600}>
            {value}
          </Typography>
        )}
      </Box>
    </CardActionArea>
  );
}

export default function MemoryStatsWidget() {
  const { data, isLoading } = useSWR<HomeBrainStats>(
    "home-brain-stats",
    fetchHomeBrainStats,
    { revalidateOnFocus: false },
  );

  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
        Brain
      </Typography>
      <Card variant="outlined">
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <StatRow
            label="Memory documents"
            value={data?.memoryCount ?? 0}
            href="/memory"
            loading={isLoading}
          />
          <Divider />
          <StatRow
            label="Custom tools"
            value={data?.toolCount ?? 0}
            href="/skills"
            loading={isLoading}
          />
        </CardContent>
      </Card>
    </Box>
  );
}

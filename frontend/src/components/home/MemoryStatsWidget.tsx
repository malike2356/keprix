"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import { SkeletonBlock } from "@/components/ui/loading";
import { fetchHomeBrainStats, type HomeBrainStats } from "@/lib/home-api";

function StatRow({ label, value, href, loading }: {
  label: string;
  value: number;
  href: string;
  loading: boolean;
}) {
  return (
    <CardActionArea component="a" href={href}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", px: 2, py: 1.25 }}>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        {loading ? (
          <SkeletonBlock height={14} width={32} />
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
            label="Memories"
            value={data?.memoryCount ?? 0}
            href="/brain/graph"
            loading={isLoading}
          />
          <Divider />
          <StatRow
            label="Skills"
            value={data?.skillCount ?? data?.toolCount ?? 0}
            href="/skills"
            loading={isLoading}
          />
          <Divider />
          <StatRow
            label="Documents"
            value={data?.documentCount ?? 0}
            href="/documents"
            loading={isLoading}
          />
          <Divider />
          <StatRow
            label="Sources"
            value={data?.sourceCount ?? 0}
            href="/brain/graph"
            loading={isLoading}
          />
        </CardContent>
      </Card>
    </Box>
  );
}

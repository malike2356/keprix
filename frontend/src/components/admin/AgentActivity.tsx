"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { DailySeries } from "@/lib/admin-dashboard-api";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type AgentActivityProps = {
  data?: DailySeries | null;
  loading?: boolean;
};

export default function AgentActivity({ data, loading }: AgentActivityProps) {
  const theme = useTheme();
  const primary = theme.palette.primary.main;

  if (loading) {
    return (
      <DashboardCard title="Agent activity">
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  const labels = data?.labels?.map((label) => label.slice(5)) || [];
  const values = data?.values || [];
  const hasActivity = values.some((value) => value > 0);

  return (
    <DashboardCard title="Agent activity" subtitle="Conversation volume (30 days)">
      {!hasActivity ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No conversation activity in the last 30 days yet.
        </Typography>
      ) : (
        <Box>
          <Chart
            type="area"
            height={280}
          series={[{ name: "Conversations", data: values }]}
          options={{
            chart: { toolbar: { show: false }, foreColor: theme.palette.text.secondary },
            colors: [primary],
            fill: { type: "gradient", gradient: { opacityFrom: 0.35, opacityTo: 0.05 } },
            dataLabels: { enabled: false },
            stroke: { curve: "smooth", width: 2 },
            xaxis: { categories: labels },
            yaxis: { labels: { formatter: (value: number) => `${Math.round(value)}` } },
            grid: { borderColor: theme.palette.divider },
            tooltip: { theme: theme.palette.mode },
          }}
        />
        </Box>
      )}
    </DashboardCard>
  );
}

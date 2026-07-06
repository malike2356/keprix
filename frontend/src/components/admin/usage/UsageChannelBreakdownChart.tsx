"use client";

import dynamic from "next/dynamic";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { UsageBreakdownRow } from "@/lib/usage-api";
import { formatUsdCost } from "@/lib/usage-format";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type UsageChannelBreakdownChartProps = {
  data?: UsageBreakdownRow[];
  loading?: boolean;
};

export default function UsageChannelBreakdownChart({ data, loading }: UsageChannelBreakdownChartProps) {
  const theme = useTheme();
  const rows = data ?? [];

  if (loading) {
    return (
      <DashboardCard title="Cost by channel">
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  if (!rows.length) {
    return (
      <DashboardCard title="Cost by channel">
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No channel breakdown for this period.
        </Typography>
      </DashboardCard>
    );
  }

  return (
    <DashboardCard title="Cost by channel" subtitle="Estimated spend grouped by ingress channel">
      <Chart
        type="bar"
        height={280}
        series={[{ name: "Cost (USD)", data: rows.map((row) => row.total_cost_usd) }]}
        options={{
          chart: { toolbar: { show: false }, foreColor: theme.palette.text.secondary },
          colors: [theme.palette.warning.main],
          plotOptions: { bar: { borderRadius: 4, columnWidth: "55%" } },
          dataLabels: { enabled: false },
          xaxis: { categories: rows.map((row) => row.label) },
          yaxis: {
            labels: {
              formatter: (value: number) => formatUsdCost(value, "estimated"),
            },
          },
          grid: { borderColor: theme.palette.divider },
          tooltip: { theme: theme.palette.mode },
        }}
      />
    </DashboardCard>
  );
}

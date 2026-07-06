"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { DailySeries } from "@/lib/admin-dashboard-api";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type MutationCompoundingSparklineProps = {
  data?: DailySeries | null;
  loading?: boolean;
};

export default function MutationCompoundingSparkline({
  data,
  loading,
}: MutationCompoundingSparklineProps) {
  const theme = useTheme();

  if (loading) {
    return (
      <DashboardCard title="Tool synthesis">
        <SkeletonChart height={120} />
      </DashboardCard>
    );
  }

  const labels = data?.labels?.map((label) => label.slice(5)) || [];
  const values = data?.values || [];
  const hasActivity = values.some((value) => value > 0);

  return (
    <DashboardCard
      title="Tool synthesis"
      subtitle="Approvals per day (30 days)"
    >
      {!hasActivity ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          No active mutations recorded yet.
        </Typography>
      ) : (
        <Box>
          <Chart
            type="bar"
            height={140}
            series={[{ name: "Approvals", data: values }]}
            options={{
              chart: { toolbar: { show: false }, background: "transparent" },
              colors: [theme.palette.secondary.main],
              plotOptions: { bar: { borderRadius: 3, columnWidth: "65%" } },
              dataLabels: { enabled: false },
              xaxis: { categories: labels, labels: { show: false } },
              yaxis: { labels: { style: { fontSize: "11px" } } },
              grid: { borderColor: theme.palette.divider, strokeDashArray: 4 },
              tooltip: { theme: theme.palette.mode },
            }}
          />
        </Box>
      )}
    </DashboardCard>
  );
}

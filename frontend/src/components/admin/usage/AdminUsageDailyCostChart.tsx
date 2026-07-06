"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import { fetchAdminUsageDaily } from "@/lib/admin-pages-api";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

export default function AdminUsageDailyCostChart() {
  const theme = useTheme();
  const { data, isLoading } = useSWR("admin-usage-daily-cost", () => fetchAdminUsageDaily(30));

  if (isLoading) {
    return (
      <DashboardCard title="Daily cost">
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  const labels = (data || []).map((point) => point.date.slice(5));
  const values = (data || []).map((point) => point.cost_usd);
  const hasData = values.some((value) => value > 0);

  return (
    <DashboardCard title="Daily cost" subtitle="Estimated LLM spend (30 days)">
      {!hasData ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No cost data in the last 30 days.
        </Typography>
      ) : (
        <Box>
          <Chart
            type="area"
            height={280}
            series={[{ name: "Cost (USD)", data: values }]}
            options={{
              chart: { toolbar: { show: false }, foreColor: theme.palette.text.secondary },
              colors: [theme.palette.warning.main],
              fill: { type: "gradient", gradient: { opacityFrom: 0.35, opacityTo: 0.05 } },
              dataLabels: { enabled: false },
              stroke: { curve: "smooth", width: 2 },
              xaxis: { categories: labels },
              yaxis: { labels: { formatter: (value: number) => `$${value.toFixed(2)}` } },
              grid: { borderColor: theme.palette.divider },
              tooltip: { theme: theme.palette.mode, y: { formatter: (value: number) => `$${value.toFixed(2)}` } },
            }}
          />
        </Box>
      )}
    </DashboardCard>
  );
}

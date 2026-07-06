"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import { fetchAdminUsageByModel } from "@/lib/admin-pages-api";
import { formatUsdCost } from "@/lib/usage-format";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

export default function AdminUsageDonut() {
  const theme = useTheme();
  const { data, isLoading } = useSWR("admin-usage-by-model-donut", () => fetchAdminUsageByModel(30));

  if (isLoading) {
    return (
      <DashboardCard title="Cost by model">
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  const rows = data || [];
  const series = rows.map((row) => row.total_cost_usd);
  const labels = rows.map((row) => row.model_id);
  const hasData = series.some((value) => value > 0);

  return (
    <DashboardCard title="Cost by model" subtitle="Estimated spend by model (30 days)">
      {!hasData ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No model usage recorded in the last 30 days.
        </Typography>
      ) : (
        <Box>
          <Chart
            type="donut"
            height={280}
            series={series}
            options={{
              chart: { type: "donut", background: "transparent", foreColor: theme.palette.text.secondary },
              labels,
              theme: { mode: theme.palette.mode },
              legend: { position: "bottom" },
              dataLabels: { enabled: false },
              plotOptions: { pie: { donut: { size: "65%" } } },
              tooltip: {
                theme: theme.palette.mode,
                y: { formatter: (value: number) => formatUsdCost(value, "estimated") },
              },
            }}
          />
          <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.5 }}>
            {rows.slice(0, 6).map((row) => (
              <Typography key={row.model_id} variant="caption" color="text.secondary">
                {row.model_id}: {formatUsdCost(row.total_cost_usd, "estimated")}
              </Typography>
            ))}
          </Box>
        </Box>
      )}
    </DashboardCard>
  );
}

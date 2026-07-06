"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { ToolBreakdown, ToolBreakdownRow } from "@/lib/admin-dashboard-api";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type ToolSynthesisBreakupProps = {
  data?: ToolBreakdown | null;
  usageRows?: ToolBreakdownRow[];
  loading?: boolean;
};

export default function ToolSynthesisBreakup({ data, usageRows = [], loading }: ToolSynthesisBreakupProps) {
  const theme = useTheme();

  if (loading) {
    return (
      <DashboardCard title="Tool synthesis">
        <SkeletonChart height={180} />
      </DashboardCard>
    );
  }

  const labels = data?.labels || ["Synthesised", "Built-in", "Community"];
  const values = data?.values || [0, 0, 0];
  const total = values.reduce((sum, value) => sum + value, 0);
  const hasUsage = usageRows.some((row) => row.call_count > 0);

  return (
    <DashboardCard title="Tool synthesis" subtitle="Source breakdown and top tool calls">
      {hasUsage ? (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
            Top tools by call volume
          </Typography>
          <Chart
            type="bar"
            height={240}
            series={[{ name: "Calls", data: usageRows.map((row) => row.call_count) }]}
            options={{
              chart: { toolbar: { show: false }, background: "transparent" },
              plotOptions: { bar: { horizontal: true, barHeight: "70%", borderRadius: 3 } },
              colors: [theme.palette.primary.main],
              dataLabels: { enabled: false },
              xaxis: { categories: usageRows.map((row) => row.tool_name) },
              tooltip: {
                y: {
                  formatter: (value: number, opts) => {
                    const row = usageRows[opts.dataPointIndex];
                    const rate = row ? Math.round(row.success_rate * 100) : 0;
                    return `${value} calls (${rate}% success)`;
                  },
                },
              },
            }}
          />
        </Box>
      ) : null}
      <Grid container spacing={2} alignItems="center">
        <Grid size={{ xs: 7 }}>
          <Typography variant="h4" fontWeight={700}>
            {total}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Active tool sources
          </Typography>
          <Stack spacing={1} sx={{ mt: 2 }}>
            {labels.map((label, index) => (
              <Typography key={label} variant="caption" color="text.secondary">
                {label}: {values[index] || 0}
              </Typography>
            ))}
          </Stack>
        </Grid>
        <Grid size={{ xs: 5 }}>
          <Box>
            <Chart
              type="donut"
              height={150}
              series={values}
              options={{
                labels,
                colors: [theme.palette.primary.main, theme.palette.secondary.main, theme.palette.success.main],
                legend: { show: false },
                dataLabels: { enabled: false },
                stroke: { show: false },
              }}
            />
          </Box>
        </Grid>
      </Grid>
    </DashboardCard>
  );
}

"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { UsageBreakdownRow } from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type UsageModelBreakdownChartProps = {
  data?: UsageBreakdownRow[];
  loading?: boolean;
  title?: string;
  onRowClick?: (key: string) => void;
};

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return reduced;
}

export default function UsageModelBreakdownChart({
  data,
  loading,
  title = "By model",
  onRowClick,
}: UsageModelBreakdownChartProps) {
  const theme = useTheme();
  const reducedMotion = usePrefersReducedMotion();
  const [showTable, setShowTable] = React.useState(false);
  const rows = data ?? [];
  const hasData = rows.length > 0;

  if (loading) {
    return (
      <DashboardCard title={title}>
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  const labels = rows.map((row) => row.label);
  const costs = rows.map((row) => row.total_cost_usd);

  return (
    <DashboardCard title={title} subtitle="Estimated spend share per period">
      {!hasData ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No breakdown for this period.
        </Typography>
      ) : reducedMotion || showTable ? (
        <Box>
          {!reducedMotion ? (
            <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
              <Button size="small" onClick={() => setShowTable(false)}>
                Show chart
              </Button>
            </Box>
          ) : null}
          <Table size="small" aria-label="Usage breakdown">
            <TableHead>
              <TableRow>
                <TableCell>Model</TableCell>
                <TableCell align="right">Tokens</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell align="right">Share</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={row.key}
                  hover={Boolean(onRowClick)}
                  sx={onRowClick ? { cursor: "pointer" } : undefined}
                  onClick={() => onRowClick?.(row.key)}
                >
                  <TableCell>{row.label}</TableCell>
                  <TableCell align="right">{formatTokenCount(row.total_tokens)}</TableCell>
                  <TableCell align="right">{formatUsdCost(row.total_cost_usd, "estimated")}</TableCell>
                  <TableCell align="right">{row.share_percent.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : (
        <Box>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
            <Button size="small" onClick={() => setShowTable(true)}>
              Show data table
            </Button>
          </Box>
          <Chart
            type="bar"
            height={280}
            series={[{ name: "Cost (USD)", data: costs }]}
            options={{
              chart: {
                toolbar: { show: false },
                foreColor: theme.palette.text.secondary,
                events: {
                  dataPointSelection: (_event, _chartContext, config) => {
                    const index = config.dataPointIndex;
                    if (typeof index === "number" && rows[index] && onRowClick) {
                      onRowClick(rows[index].key);
                    }
                  },
                },
              },
              colors: [theme.palette.secondary.main],
              plotOptions: {
                bar: { horizontal: true, borderRadius: 4, barHeight: "70%" },
              },
              dataLabels: { enabled: false },
              xaxis: {
                categories: labels,
                labels: {
                  formatter: (value: string) => formatUsdCost(Number(value), "estimated"),
                },
              },
              grid: { borderColor: theme.palette.divider },
              tooltip: { theme: theme.palette.mode },
            }}
          />
        </Box>
      )}
    </DashboardCard>
  );
}

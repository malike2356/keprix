"use client";

import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import type { UsageTimeseriesPoint } from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

type UsageTimeseriesChartProps = {
  data?: UsageTimeseriesPoint[];
  loading?: boolean;
};

type MetricMode = "tokens" | "cost";

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

export default function UsageTimeseriesChart({ data, loading }: UsageTimeseriesChartProps) {
  const theme = useTheme();
  const reducedMotion = usePrefersReducedMotion();
  const [metric, setMetric] = React.useState<MetricMode>("tokens");
  const [showTable, setShowTable] = React.useState(false);

  if (loading) {
    return (
      <DashboardCard title="Usage over time">
        <SkeletonChart height={280} />
      </DashboardCard>
    );
  }

  const points = data ?? [];
  const labels = points.map((point) => point.date.slice(5));
  const tokenValues = points.map((point) => point.total_tokens);
  const costValues = points.map((point) => point.total_cost_usd);
  const hasData = points.some((point) => point.request_count > 0);

  const seriesName = metric === "tokens" ? "Tokens" : "Cost (USD)";
  const seriesData = metric === "tokens" ? tokenValues : costValues;

  return (
    <DashboardCard
      title="Usage over time"
      subtitle="Daily token volume and estimated spend"
      action={
        <ToggleButtonGroup
          size="small"
          exclusive
          value={metric}
          onChange={(_event, next: MetricMode | null) => {
            if (next) {
              setMetric(next);
            }
          }}
          aria-label="Usage metric"
        >
          <ToggleButton value="tokens">Tokens</ToggleButton>
          <ToggleButton value="cost">Cost</ToggleButton>
        </ToggleButtonGroup>
      }
    >
      {!hasData ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
          No usage recorded for this period.
        </Typography>
      ) : reducedMotion || showTable ? (
        <Box>
          <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
            {!reducedMotion ? (
              <Button size="small" onClick={() => setShowTable(false)}>
                Show chart
              </Button>
            ) : null}
          </Box>
          <Table size="small" aria-label="Usage timeseries data">
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell align="right">Tokens</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell align="right">Calls</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {points.map((point) => (
                <TableRow key={point.date}>
                  <TableCell>{point.date}</TableCell>
                  <TableCell align="right">{formatTokenCount(point.total_tokens)}</TableCell>
                  <TableCell align="right">{formatUsdCost(point.total_cost_usd, "estimated")}</TableCell>
                  <TableCell align="right">{point.request_count}</TableCell>
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
            type="area"
            height={280}
            series={[{ name: seriesName, data: seriesData }]}
            options={{
              chart: { toolbar: { show: false }, foreColor: theme.palette.text.secondary },
              colors: [theme.palette.primary.main],
              fill: { type: "gradient", gradient: { opacityFrom: 0.35, opacityTo: 0.05 } },
              dataLabels: { enabled: false },
              stroke: { curve: "smooth", width: 2 },
              xaxis: { categories: labels },
              yaxis: {
                labels: {
                  formatter: (value: number) =>
                    metric === "tokens" ? formatTokenCount(value) : formatUsdCost(value, "estimated"),
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

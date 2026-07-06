"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import {
  IconApi,
  IconCash,
  IconCoin,
  IconHash,
} from "@tabler/icons-react";
import Link from "next/link";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import UsageBudgetBanner from "@/components/usage/UsageBudgetBanner";
import UsageModelBreakdownChart from "@/components/usage/UsageModelBreakdownChart";
import UsagePeriodToolbar from "@/components/usage/UsagePeriodToolbar";
import UsageRecentTable from "@/components/usage/UsageRecentTable";
import UsageStatCard from "@/components/usage/UsageStatCard";
import UsageTimeseriesChart from "@/components/usage/UsageTimeseriesChart";
import {
  fetchUsageBreakdown,
  fetchUsageBudget,
  fetchUsageEvents,
  fetchUsageSummary,
  fetchUsageTimeseries,
  readStoredUsagePeriod,
  type UsagePeriodDays,
} from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

export default function UsagePage() {
  const [periodDays, setPeriodDays] = React.useState<UsagePeriodDays>(30);

  React.useEffect(() => {
    setPeriodDays(readStoredUsagePeriod());
  }, []);

  const query = React.useMemo(() => ({ days: periodDays }), [periodDays]);

  const { data: summary, isLoading: summaryLoading } = useSWR(
    `usage-summary-${periodDays}`,
    () => fetchUsageSummary(query),
  );
  const { data: timeseries, isLoading: timeseriesLoading } = useSWR(
    `usage-timeseries-${periodDays}-day`,
    () => fetchUsageTimeseries({ ...query, granularity: "day" }),
  );
  const { data: breakdown, isLoading: breakdownLoading } = useSWR(
    `usage-breakdown-model-${periodDays}`,
    () => fetchUsageBreakdown("model", query),
  );
  const { data: events, isLoading: eventsLoading } = useSWR(
    `usage-events-${periodDays}`,
    () => fetchUsageEvents({ ...query, limit: 20 }),
  );
  const { data: budget } = useSWR("usage-budget", () => fetchUsageBudget());

  const isEmpty = !summaryLoading && (summary?.request_count ?? 0) === 0;

  return (
    <Box>
      <PageHeader
        title="LLM usage and cost"
        description="Token consumption and estimated spend for your account."
      />
      <UsageBudgetBanner budget={budget} />
      <UsagePeriodToolbar value={periodDays} onChange={setPeriodDays} />

      {isEmpty ? (
        <Box
          sx={{
            border: 1,
            borderColor: "divider",
            borderRadius: 2,
            p: 4,
            textAlign: "center",
          }}
        >
          <Typography variant="h6" sx={{ mb: 1 }}>
            No LLM usage recorded yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Usage appears after you send messages in chat or run agent workflows.
          </Typography>
          <Button component={Link} href="/chat" variant="contained">
            Open chat
          </Button>
        </Box>
      ) : (
        <>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
              mb: 3,
            }}
          >
            <UsageStatCard
              title="Total tokens"
              value={formatTokenCount(summary?.total_tokens ?? 0)}
              icon={<IconHash size={22} />}
              color="primary"
              loading={summaryLoading}
            />
            <UsageStatCard
              title="Estimated cost (USD)"
              value={formatUsdCost(summary?.total_cost_usd ?? 0, "estimated")}
              icon={<IconCash size={22} />}
              color="success"
              loading={summaryLoading}
            />
            <UsageStatCard
              title="API calls"
              value={(summary?.request_count ?? 0).toLocaleString()}
              icon={<IconApi size={22} />}
              color="info"
              loading={summaryLoading}
            />
            <UsageStatCard
              title="Avg cost per call"
              value={formatUsdCost(summary?.avg_cost_per_request_usd ?? 0, "estimated")}
              icon={<IconCoin size={22} />}
              color="warning"
              loading={summaryLoading}
            />
          </Box>

          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              mb: 3,
            }}
          >
            <UsageTimeseriesChart data={timeseries} loading={timeseriesLoading} />
            <UsageModelBreakdownChart data={breakdown} loading={breakdownLoading} />
          </Box>

          <UsageRecentTable items={events?.items} loading={eventsLoading} />
        </>
      )}
    </Box>
  );
}

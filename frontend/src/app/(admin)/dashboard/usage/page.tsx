"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  IconApi,
  IconCash,
  IconCoin,
  IconHash,
} from "@tabler/icons-react";
import * as React from "react";
import useSWR from "swr";
import PageContainer from "@/components/shared/PageContainer";
import AdminUsageDailyCostChart from "@/components/admin/usage/AdminUsageDailyCostChart";
import AdminUsageDonut from "@/components/admin/usage/AdminUsageDonut";
import UsageBudgetPanel from "@/components/admin/usage/UsageBudgetPanel";
import UsageAdminEventLog from "@/components/admin/usage/UsageAdminEventLog";
import UsageChannelBreakdownChart from "@/components/admin/usage/UsageChannelBreakdownChart";
import UsageModelBreakdownTable from "@/components/admin/usage/UsageModelBreakdownTable";
import UsageUserBreakdownTable from "@/components/admin/usage/UsageUserBreakdownTable";
import UsageStatCard from "@/components/usage/UsageStatCard";
import UsageTimeseriesChart from "@/components/usage/UsageTimeseriesChart";
import { useRequireAdmin } from "@/lib/ce-auth";
import {
  downloadUsageExport,
  fetchUsageBreakdown,
  fetchUsageBudget,
  fetchUsageEvents,
  fetchUsageSummary,
  fetchUsageTimeseries,
  updateUsageBudget,
} from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

const PERIOD_DAYS = 30;

export default function AdminUsagePage() {
  useRequireAdmin();
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(50);
  const [budgetMessage, setBudgetMessage] = React.useState<string | null>(null);
  const [budgetError, setBudgetError] = React.useState<string | null>(null);
  const [savingBudget, setSavingBudget] = React.useState(false);
  const [exporting, setExporting] = React.useState(false);

  const query = React.useMemo(() => ({ days: PERIOD_DAYS }), []);

  const { data: summary, isLoading: summaryLoading } = useSWR("admin-usage-summary-30", () =>
    fetchUsageSummary(query),
  );
  const { data: timeseries, isLoading: timeseriesLoading } = useSWR("admin-usage-timeseries-30", () =>
    fetchUsageTimeseries({ ...query, granularity: "day" }),
  );
  const { data: channelBreakdown, isLoading: channelLoading } = useSWR("admin-usage-channel-30", () =>
    fetchUsageBreakdown("channel", query),
  );
  const { data: userBreakdown, isLoading: userLoading } = useSWR("admin-usage-user-30", () =>
    fetchUsageBreakdown("user", query),
  );
  const { data: modelBreakdown, isLoading: modelLoading } = useSWR("admin-usage-model-30", () =>
    fetchUsageBreakdown("model", query),
  );
  const { data: budget, mutate: mutateBudget } = useSWR("admin-usage-budget", () => fetchUsageBudget());
  const { data: events, isLoading: eventsLoading } = useSWR(
    `admin-usage-events-${page}-${rowsPerPage}`,
    () => fetchUsageEvents({ ...query, limit: rowsPerPage, offset: page * rowsPerPage }),
  );

  const handleSaveBudget = async (body: {
    monthly_budget_usd: number | null;
    alert_threshold_percent: number;
  }) => {
    setSavingBudget(true);
    setBudgetMessage(null);
    setBudgetError(null);
    try {
      await updateUsageBudget(body);
      await mutateBudget();
      setBudgetMessage("Budget saved");
    } catch (err) {
      setBudgetError(err instanceof Error ? err.message : "Failed to save budget");
    } finally {
      setSavingBudget(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadUsageExport(PERIOD_DAYS);
    } catch (err) {
      setBudgetError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <PageContainer
      title="LLM usage"
      description="Instance-wide token consumption, estimated spend, budgets, and export."
      padded={false}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <UsageBudgetPanel
          budget={budget}
          onSave={handleSaveBudget}
          saving={savingBudget}
          message={budgetMessage}
          error={budgetError}
        />

        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <AdminUsageDonut />
          <AdminUsageDailyCostChart />
        </Box>

        <Box
          sx={{
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", xl: "repeat(4, 1fr)" },
          }}
        >
          <UsageStatCard
            title="Total tokens"
            value={formatTokenCount(summary?.total_tokens ?? 0)}
            icon={<IconHash size={22} />}
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

        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
          <UsageTimeseriesChart data={timeseries} loading={timeseriesLoading} />
          <UsageChannelBreakdownChart data={channelBreakdown} loading={channelLoading} />
        </Box>

        <UsageUserBreakdownTable rows={userBreakdown} loading={userLoading} />
        <UsageModelBreakdownTable rows={modelBreakdown} loading={modelLoading} limit={20} />

        <UsageAdminEventLog
          items={events?.items}
          total={events?.total ?? 0}
          loading={eventsLoading}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={setPage}
          onRowsPerPageChange={(next) => {
            setRowsPerPage(next);
            setPage(0);
          }}
          onExport={() => void handleExport()}
          exporting={exporting}
        />

        {summary?.unknown_cost_count ? (
          <Typography variant="caption" color="text.secondary">
            {summary.unknown_cost_count} events have unknown pricing in this period.
          </Typography>
        ) : null}
      </Box>
    </PageContainer>
  );
}

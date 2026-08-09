"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconApi, IconCash, IconCoin, IconHash } from "@tabler/icons-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import UsageBudgetPanel from "@/components/admin/usage/UsageBudgetPanel";
import UsageBudgetBanner from "@/components/usage/UsageBudgetBanner";
import UsageModelBreakdownChart from "@/components/usage/UsageModelBreakdownChart";
import UsagePeriodToolbar from "@/components/usage/UsagePeriodToolbar";
import UsageRecentTable from "@/components/usage/UsageRecentTable";
import UsageStatCard from "@/components/usage/UsageStatCard";
import UsageTimeseriesChart from "@/components/usage/UsageTimeseriesChart";
import {
  downloadUsageExport,
  fetchUsageBreakdown,
  fetchUsageBudget,
  fetchUsageEvents,
  fetchUsageStatus,
  fetchUsageSummary,
  fetchUsageTimeseries,
  readStoredUsagePeriod,
  storeUsagePeriod,
  updateUsageBudget,
  USAGE_PERIOD_OPTIONS,
  type UsagePeriodDays,
  type UsageQueryParams,
} from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

function coercePeriod(raw: string | null | undefined): UsagePeriodDays {
  const n = Number(raw);
  if (USAGE_PERIOD_OPTIONS.includes(n as UsagePeriodDays)) return n as UsagePeriodDays;
  return readStoredUsagePeriod();
}

export default function UsagePanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [periodDays, setPeriodDays] = React.useState<UsagePeriodDays>(30);
  const [provider, setProvider] = React.useState("");
  const [model, setModel] = React.useState("");
  const [channel, setChannel] = React.useState("");
  const [userId, setUserId] = React.useState("");
  const [dayFilter, setDayFilter] = React.useState<string | null>(null);
  const [exportError, setExportError] = React.useState<string | null>(null);
  const [exportBusy, setExportBusy] = React.useState(false);
  const [budgetSaving, setBudgetSaving] = React.useState(false);
  const [budgetMessage, setBudgetMessage] = React.useState<string | null>(null);
  const [budgetError, setBudgetError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setPeriodDays(coercePeriod(searchParams.get("days")));
    setProvider(searchParams.get("provider") || "");
    setModel(searchParams.get("model") || "");
    setChannel(searchParams.get("channel") || "");
    setUserId(searchParams.get("user_id") || "");
    setDayFilter(searchParams.get("day"));
  }, [searchParams]);

  const replaceParams = React.useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (!value) next.delete(key);
        else next.set(key, value);
      }
      next.set("tab", "usage");
      router.replace(`/data?${next.toString()}`);
    },
    [router, searchParams],
  );

  const setPeriod = (days: UsagePeriodDays) => {
    storeUsagePeriod(days);
    setPeriodDays(days);
    replaceParams({ days: String(days) });
  };

  const query = React.useMemo<UsageQueryParams>(
    () => ({
      days: periodDays,
      provider: provider || undefined,
      model: model || undefined,
      channel: channel || undefined,
      user_id: userId || undefined,
    }),
    [periodDays, provider, model, channel, userId],
  );

  const eventQuery = React.useMemo<UsageQueryParams>(() => {
    if (!dayFilter) return query;
    return {
      ...query,
      from_ts: `${dayFilter}T00:00:00.000Z`,
      to_ts: `${dayFilter}T23:59:59.999Z`,
    };
  }, [query, dayFilter]);

  const { data: metering } = useSWR("usage-metering-status", fetchUsageStatus);
  const { data: summary, error: summaryError, isLoading: summaryLoading } = useSWR(
    metering?.enabled === false ? null : ["usage-summary", query],
    () => fetchUsageSummary(query),
  );
  const { data: timeseries, isLoading: timeseriesLoading } = useSWR(
    metering?.enabled === false ? null : ["usage-timeseries", query],
    () => fetchUsageTimeseries({ ...query, granularity: "day" }),
  );
  const { data: breakdown, isLoading: breakdownLoading } = useSWR(
    metering?.enabled === false ? null : ["usage-breakdown-model", query],
    () => fetchUsageBreakdown("model", query),
  );
  const { data: agentBreakdown, isLoading: agentBreakdownLoading } = useSWR(
    metering?.enabled === false ? null : ["usage-breakdown-agent", query],
    () => fetchUsageBreakdown("agent", query),
  );
  const { data: providerBreakdown } = useSWR(
    metering?.enabled === false ? null : ["usage-breakdown-provider", query],
    () => fetchUsageBreakdown("provider", query),
  );
  const { data: channelBreakdown } = useSWR(
    metering?.enabled === false ? null : ["usage-breakdown-channel", query],
    () => fetchUsageBreakdown("channel", query),
  );
  const { data: events, isLoading: eventsLoading } = useSWR(
    metering?.enabled === false ? null : ["usage-events", eventQuery],
    () => fetchUsageEvents({ ...eventQuery, limit: 40 }),
  );
  const { data: budget, mutate: mutateBudget } = useSWR(
    metering?.enabled === false ? null : "usage-budget",
    () => fetchUsageBudget(),
  );

  const isEmpty = metering?.enabled !== false && !summaryLoading && (summary?.request_count ?? 0) === 0;
  const providerOptions = (providerBreakdown ?? []).map((row) => row.key).filter(Boolean);
  const modelOptions = (breakdown ?? []).map((row) => row.key).filter(Boolean);
  const channelOptions = (channelBreakdown ?? []).map((row) => row.key).filter(Boolean);

  const handleExport = async (format: "csv" | "json") => {
    setExportBusy(true);
    setExportError(null);
    try {
      await downloadUsageExport(periodDays, { ...query, format });
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExportBusy(false);
    }
  };

  const handleBudgetSave = async (body: {
    monthly_budget_usd: number | null;
    alert_threshold_percent: number;
  }) => {
    setBudgetSaving(true);
    setBudgetError(null);
    setBudgetMessage(null);
    try {
      await updateUsageBudget(body);
      await mutateBudget();
      setBudgetMessage("Budget saved.");
    } catch (err) {
      setBudgetError(err instanceof Error ? err.message : "Could not save budget");
    } finally {
      setBudgetSaving(false);
    }
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
        <Button
          size="small"
          variant="outlined"
          disabled={exportBusy || metering?.enabled === false}
          onClick={() => void handleExport("csv")}
        >
          Export CSV
        </Button>
        <Button
          size="small"
          variant="outlined"
          disabled={exportBusy || metering?.enabled === false}
          onClick={() => void handleExport("json")}
        >
          Export JSON
        </Button>
        <Button component="a" href="/data?tab=observability" size="small" variant="text">
          Observability
        </Button>
      </Stack>

      {exportError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {exportError}
        </Alert>
      ) : null}
      {summaryError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {summaryError instanceof Error ? summaryError.message : "Could not load usage"}
        </Alert>
      ) : null}

      {metering?.enabled === false ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          LLM usage metering is disabled. {metering.enable_hint} Then send a chat message to produce
          events.
        </Alert>
      ) : null}

      <UsageBudgetBanner budget={budget} />
      <UsagePeriodToolbar value={periodDays} onChange={setPeriod} />

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label="Provider"
          value={provider}
          onChange={(event) => replaceParams({ provider: event.target.value || null })}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="">All</MenuItem>
          {providerOptions.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Model"
          value={model}
          onChange={(event) => replaceParams({ model: event.target.value || null })}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {modelOptions.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label="Channel / agent"
          value={channel}
          onChange={(event) => replaceParams({ channel: event.target.value || null })}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {channelOptions.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </TextField>
        {metering?.is_admin ? (
          <TextField
            size="small"
            label="User id"
            value={userId}
            onChange={(event) => replaceParams({ user_id: event.target.value.trim() || null })}
            sx={{ minWidth: 160 }}
          />
        ) : null}
        {dayFilter ? (
          <Button size="small" onClick={() => replaceParams({ day: null })}>
            Clear day {dayFilter}
          </Button>
        ) : null}
      </Stack>

      {budget ? (
        <Box sx={{ mb: 3 }}>
          {metering?.is_admin ? (
            <UsageBudgetPanel
              budget={budget}
              onSave={handleBudgetSave}
              saving={budgetSaving}
              message={budgetMessage}
              error={budgetError}
            />
          ) : (
            <Alert severity="info" sx={{ mb: 0 }}>
              Budget: {formatUsdCost(budget.spent_usd, "estimated")} spent
              {budget.monthly_budget_usd != null
                ? ` of ${formatUsdCost(budget.monthly_budget_usd, "estimated")}`
                : " (no monthly limit set)"}
              .{" "}
              <Link href="/dashboard/usage">Admins can edit budgets in admin usage</Link>
              {" or ask an admin to set KEPRIX budget settings."}
            </Alert>
          )}
        </Box>
      ) : null}

      {metering?.enabled === false ? null : isEmpty ? (
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
          <Button component="a" href="/chat" variant="contained">
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
            <UsageTimeseriesChart
              data={timeseries}
              loading={timeseriesLoading}
              onPointClick={(date) => replaceParams({ day: date })}
            />
            <UsageModelBreakdownChart
              data={breakdown}
              loading={breakdownLoading}
              title="By model"
              onRowClick={(key) => replaceParams({ model: key })}
            />
          </Box>

          <Box sx={{ mb: 3 }}>
            <UsageModelBreakdownChart
              data={agentBreakdown}
              loading={agentBreakdownLoading}
              title="By agent"
              onRowClick={(key) => replaceParams({ channel: key })}
            />
          </Box>

          <UsageRecentTable
            items={events?.items}
            loading={eventsLoading}
            subtitle={
              dayFilter
                ? `Events for ${dayFilter} (click the chart again or clear day to reset)`
                : "Latest LLM calls for your account"
            }
          />
        </>
      )}
    </Box>
  );
}

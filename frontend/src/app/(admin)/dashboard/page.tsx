"use client";

import Box from "@mui/material/Box";
import {
  IconCurrencyDollar,
  IconGitBranch,
  IconMessages,
  IconShieldLock,
  IconTools,
} from "@tabler/icons-react";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import AgentActivity from "@/components/admin/AgentActivity";
import ChannelHealthStrip from "@/components/admin/ChannelHealthStrip";
import MutationCompoundingSparkline from "@/components/admin/MutationCompoundingSparkline";
import RecentConversations from "@/components/admin/RecentConversations";
import RecentMutations from "@/components/admin/RecentMutations";
import StatCard from "@/components/admin/StatCard";
import ToolSynthesisBreakup from "@/components/admin/ToolSynthesisBreakup";
import CompoundingMetricsCard from "@/components/mutation/CompoundingMetricsCard";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import {
  fetchChannelStatus,
  fetchConversationDaily,
  fetchDashboardStats,
  fetchMutationActiveDaily,
  fetchRecentConversations,
  fetchRecentMutations,
  fetchToolBreakdown,
  fetchToolUsageBreakdown,
} from "@/lib/admin-dashboard-api";
import { useMutationStats, useCompoundingMetrics } from "@/lib/mutation-api";
import { formatUsdCost } from "@/lib/usage-format";

export default function AdminDashboardPage() {
  const { data: stats, isLoading: statsLoading } = useSWR("admin-stats", fetchDashboardStats);
  const { data: daily, isLoading: dailyLoading } = useSWR("admin-daily", fetchConversationDaily);
  const { data: mutationDaily, isLoading: mutationDailyLoading } = useSWR(
    "admin-mutation-daily",
    fetchMutationActiveDaily,
  );
  const { data: breakdown, isLoading: breakdownLoading } = useSWR("admin-breakdown", fetchToolBreakdown);
  const { data: toolUsage, isLoading: toolUsageLoading } = useSWR(
    "admin-tool-usage",
    () => fetchToolUsageBreakdown(8),
  );
  const { data: mutations, isLoading: mutationsLoading } = useSWR("admin-mutations", () => fetchRecentMutations(5));
  const { data: conversations, isLoading: conversationsLoading } = useSWR(
    "admin-conversations",
    () => fetchRecentConversations(5),
  );
  const { data: channels, isLoading: channelsLoading } = useSWR("admin-channels", fetchChannelStatus);
  const { data: mutationStats } = useMutationStats();
  const { data: compounding, isLoading: compoundingLoading } = useCompoundingMetrics();
  const stagedCount = mutationStats?.staged ?? 0;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {stagedCount > 0 ? (
        <Alert
          severity="warning"
          action={
            <Button component="a" href="/admin/mutations?status=staged" color="inherit" size="small">
              Review
            </Button>
          }
        >
          {stagedCount} tool{stagedCount !== 1 ? "s" : ""} awaiting your approval.
        </Alert>
      ) : null}
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
          Admin overview
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Instance operations, usage, tool approvals, memory, and channel health.
        </Typography>
        <Button component="a" href="/admin/credentials" size="small" startIcon={<IconShieldLock size={16} />} sx={{ mt: 1 }}>
          Credential audit
        </Button>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            lg: "repeat(4, 1fr)",
          },
        }}
      >
        <StatCard
          title="Conversations"
          value={stats?.conversations ?? 0}
          delta={
            stats?.conversationsToday !== undefined
              ? `${stats.conversationsToday} today`
              : undefined
          }
          positive
          loading={statsLoading}
          icon={<IconMessages size={22} stroke={1.75} />}
          color="primary"
          href="/admin/conversations"
        />
        <StatCard
          title="Tools synthesised"
          value={stats?.mutationsApproved ?? 0}
          loading={statsLoading}
          icon={<IconTools size={22} stroke={1.75} />}
          color="secondary"
          href="/admin/mutations"
        />
        <StatCard
          title="LLM cost (MTD)"
          value={formatUsdCost(stats?.llmSpend30d ?? 0)}
          loading={statsLoading}
          icon={<IconCurrencyDollar size={22} stroke={1.75} />}
          color="success"
          href="/admin/usage"
        />
        <StatCard
          title="Active agents"
          value={stats?.activeAgents ?? 0}
          loading={statsLoading}
          icon={<IconGitBranch size={22} stroke={1.75} />}
          color="info"
        />
      </Box>

      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 8 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <AgentActivity data={daily} loading={dailyLoading} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <CompoundingMetricsCard metrics={compounding} loading={compoundingLoading} />
          </Box>
        </Grid>
      </Grid>

      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 8 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <ToolSynthesisBreakup
              data={breakdown}
              usageRows={toolUsage}
              loading={breakdownLoading || toolUsageLoading}
            />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <MutationCompoundingSparkline data={mutationDaily} loading={mutationDailyLoading} />
          </Box>
        </Grid>
      </Grid>

      <Grid container spacing={2} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 8 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <RecentMutations rows={mutations} loading={mutationsLoading} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }} sx={{ display: "flex" }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <RecentConversations rows={conversations} loading={conversationsLoading} />
          </Box>
        </Grid>
      </Grid>

      <ChannelHealthStrip channels={channels} loading={channelsLoading} />
    </Box>
  );
}

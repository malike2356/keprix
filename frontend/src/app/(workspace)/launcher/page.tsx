"use client";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import useSWR from "swr";
import GreetingBar from "@/components/home/GreetingBar";
import RecentConversationsWidget from "@/components/home/RecentConversationsWidget";
import MemoryStatsWidget from "@/components/home/MemoryStatsWidget";
import TasksWidget from "@/components/home/TasksWidget";
import DiscoveryCard from "@/components/home/DiscoveryCard";
import WelcomeEmptyState from "@/components/home/WelcomeEmptyState";
import { fetchConversations, type WorkspaceSession } from "@/lib/workspace-api";
import { fetchDashboardStats, type DashboardStats } from "@/lib/admin-dashboard-api";

export default function LauncherPage() {
  const { data: sessions } = useSWR<WorkspaceSession[]>(
    "home-conversations",
    () => fetchConversations(5),
    { revalidateOnFocus: false },
  );

  const { data: stats } = useSWR<DashboardStats>(
    "home-stats",
    fetchDashboardStats,
    { revalidateOnFocus: false },
  );

  const conversationCount = sessions?.length ?? 0;
  const memoryCount = stats?.memoryDocuments ?? 0;
  const toolCount = stats?.tools ?? 0;

  const isEmpty = sessions !== undefined && sessions.length === 0;

  if (isEmpty) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Box sx={{ px: 4, pt: 4, pb: 3, borderBottom: "1px solid", borderColor: "divider" }}>
          <GreetingBar />
        </Box>
        <WelcomeEmptyState />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1080, mx: "auto", px: { xs: 2, sm: 4 }, py: 4, pb: 12 }}>
      <GreetingBar />

      <Grid container spacing={3} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 7, lg: 8 }}>
          <RecentConversationsWidget />
        </Grid>
        <Grid size={{ xs: 12, md: 5, lg: 4 }}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <MemoryStatsWidget />
            <TasksWidget />
          </Box>
        </Grid>
      </Grid>

      <DiscoveryCard
        conversationCount={conversationCount}
        memoryCount={memoryCount}
        toolCount={toolCount}
      />
    </Box>
  );
}

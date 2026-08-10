"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import useSWR from "swr";
import GreetingBar from "@/components/home/GreetingBar";
import RecentConversationsWidget from "@/components/home/RecentConversationsWidget";
import MemoryStatsWidget from "@/components/home/MemoryStatsWidget";
import TasksWidget from "@/components/home/TasksWidget";
import DiscoveryCard from "@/components/home/DiscoveryCard";
import { fetchConversations, type WorkspaceSession } from "@/lib/workspace-api";
import { fetchHomeBrainStats, type HomeBrainStats } from "@/lib/home-api";

const QUICK_LINKS = [
  { href: "/files", title: "Files", body: "Browse the filesystem and preview text or image files." },
  { href: "/documents", title: "Documents", body: "Open workspace documents and uploads." },
  { href: "/notes", title: "Notes", body: "Review saved notes and references." },
];

export default function HomePageShell() {
  const { data: sessions } = useSWR<WorkspaceSession[]>(
    "home-conversations",
    () => fetchConversations(5),
    { revalidateOnFocus: false, shouldRetryOnError: false, dedupingInterval: 10_000 },
  );

  const { data: stats } = useSWR<HomeBrainStats>(
    "home-brain-stats",
    fetchHomeBrainStats,
    { revalidateOnFocus: false, shouldRetryOnError: false, dedupingInterval: 10_000 },
  );

  const conversationCount = sessions?.length ?? 0;
  const memoryCount = stats?.memoryCount ?? 0;
  const toolCount = stats?.toolCount ?? 0;

  // Always keep the home dashboard shell. Do not swap to the chat welcome empty
  // state after conversations resolve; that caused a visible layout jump on /home.
  return (
    <Box sx={{ maxWidth: 1080, mx: "auto", px: { xs: 2, sm: 4 }, py: 4, pb: 12 }}>
      <GreetingBar />

      <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" }, mb: 3 }}>
        {QUICK_LINKS.map((link) => (
          <Card key={link.href} variant="outlined">
            <CardActionArea component="a" href={link.href} sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  {link.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {link.body}
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Box>

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

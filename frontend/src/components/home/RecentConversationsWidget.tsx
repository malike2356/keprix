"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Skeleton from "@mui/material/Skeleton";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import NextLink from "next/link";
import useSWR from "swr";
import { fetchConversations, type WorkspaceSession } from "@/lib/workspace-api";

function relativeTime(iso?: string): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

function ConversationCard({ session }: { session: WorkspaceSession }) {
  return (
    <Card variant="outlined" sx={{ mb: 1.5 }}>
      <CardActionArea component={NextLink} href={`/chat/${session.id}`}>
        <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 1 }}>
            <Typography
              variant="body2"
              fontWeight={500}
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                flex: 1,
              }}
            >
              {session.title || "Untitled session"}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
              {relativeTime(session.updated_at ?? session.created_at)}
            </Typography>
          </Box>
          {session.preview ? (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: "block",
                mt: 0.5,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {typeof session.preview === "string" ? session.preview : ""}
            </Typography>
          ) : null}
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

function ConversationCardSkeleton() {
  return (
    <Card variant="outlined" sx={{ mb: 1.5 }}>
      <CardContent sx={{ py: 1.5, px: 2, "&:last-child": { pb: 1.5 } }}>
        <Skeleton variant="text" width="70%" />
        <Skeleton variant="text" width="40%" height={14} />
      </CardContent>
    </Card>
  );
}

export default function RecentConversationsWidget() {
  const { data: sessions, isLoading, error } = useSWR<WorkspaceSession[]>(
    "home-conversations",
    () => fetchConversations(5),
    { revalidateOnFocus: false },
  );

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight={600}>
          Recent sessions
        </Typography>
        <Link
          component={NextLink}
          href="/chat"
          variant="caption"
          color="text.secondary"
          underline="hover"
        >
          See all
        </Link>
      </Box>

      {isLoading ? (
        <>
          <ConversationCardSkeleton />
          <ConversationCardSkeleton />
          <ConversationCardSkeleton />
        </>
      ) : error ? (
        <Typography variant="body2" color="error">
          Could not load sessions.
        </Typography>
      ) : !sessions || sessions.length === 0 ? (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              No sessions yet. Start a conversation to get going.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        sessions.map((s) => <ConversationCard key={s.id} session={s} />)
      )}
    </Box>
  );
}

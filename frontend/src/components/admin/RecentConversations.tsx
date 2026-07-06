"use client";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemAvatar from "@mui/material/ListItemAvatar";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonChart } from "@/components/ui/loading";
import { formatTimeAgo } from "@/lib/time-ago";
import type { ConversationRow } from "@/lib/admin-dashboard-api";

type RecentConversationsProps = {
  rows?: ConversationRow[];
  loading?: boolean;
};

export default function RecentConversations({ rows = [], loading }: RecentConversationsProps) {
  return (
    <DashboardCard title="Recent conversations" subtitle="Latest agent sessions">
      {loading ? (
        <SkeletonChart height={220} />
      ) : rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No conversations yet.
        </Typography>
      ) : (
        <List dense>
          {rows.map((row) => (
            <ListItem key={row.id} disablePadding>
              <ListItemButton
                component={NextLink}
                href={`/admin/conversations?id=${row.id}`}
                sx={{ px: 0, borderRadius: 1 }}
              >
                <ListItemAvatar>
                  <Avatar sx={{ width: 32, height: 32, fontSize: "0.8rem" }}>
                    {(row.title || "C").slice(0, 1).toUpperCase()}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={row.title}
                  secondary={
                    <Box component="span" sx={{ display: "block" }}>
                      <Typography component="span" variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                        {row.model || "default"}
                      </Typography>
                      <Typography component="span" variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                        {row.message_count ?? 0} messages
                      </Typography>
                      <Typography component="span" variant="caption" color="text.secondary">
                        {formatTimeAgo(row.updated_at || row.created_at) || "Recently"}
                      </Typography>
                    </Box>
                  }
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      )}
    </DashboardCard>
  );
}

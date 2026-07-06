"use client";

import AddIcon from "@mui/icons-material/Add";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import Scrollbar from "@/components/shared/Scrollbar";
import { useStartNewConversation } from "@/hooks/useStartNewConversation";
import { useCESession } from "@/lib/ce-auth";
import { dateGroup, formatTimeAgo, type DateGroup } from "@/lib/time-ago";
import { deleteConversation, fetchConversations, type WorkspaceSession } from "@/lib/workspace-api";

const SIDEBAR_WIDTH = 280;
const GROUP_ORDER: DateGroup[] = ["Today", "Yesterday", "Older"];

function groupSessions(sessions: WorkspaceSession[]) {
  const groups: Record<DateGroup, WorkspaceSession[]> = {
    Today: [],
    Yesterday: [],
    Older: [],
  };
  for (const session of sessions) {
    groups[dateGroup(session.updated_at || session.created_at)].push(session);
  }
  return groups;
}

export default function WorkspaceSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useCESession();
  const { data, mutate } = useSWR("workspace-sessions", () => fetchConversations(50), {
    refreshInterval: 30_000,
  });
  const sessions = data || [];
  const grouped = groupSessions(sessions);
  const isOwner = user?.role === "admin" || user?.role === "owner";
  const { startNewConversation, starting } = useStartNewConversation();

  const onDelete = async (sessionId: string) => {
    await deleteConversation(sessionId);
    await mutate();
    if (pathname === `/chat/${sessionId}`) {
      router.push("/chat");
    }
  };

  return (
    <Box
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        height: "100%",
        overflow: "hidden",
        borderRight: 1,
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
      }}
    >
      <Box sx={{ flexShrink: 0, p: 2 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<AddIcon />}
          disabled={starting}
          onClick={() => void startNewConversation()}
        >
          New conversation
        </Button>
      </Box>
      <Scrollbar sx={{ flex: 1, minHeight: 0 }}>
        <List dense disablePadding sx={{ px: 1 }}>
          {GROUP_ORDER.map((label) => {
            const items = grouped[label];
            if (!items.length) return null;
            return (
              <Box key={label} sx={{ mb: 1 }}>
                <Typography variant="overline" color="text.secondary" sx={{ px: 1.5 }}>
                  {label}
                </Typography>
                {items.map((session) => {
                  const active = pathname === `/chat/${session.id}`;
                  return (
                    <ListItemButton
                      key={session.id}
                      component={NextLink}
                      href={`/chat/${session.id}`}
                      selected={active}
                      sx={{
                        borderRadius: 1,
                        mb: 0.5,
                        borderLeft: active ? 3 : 0,
                        borderColor: "primary.main",
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <ChatBubbleOutlineIcon fontSize="small" />
                      </ListItemIcon>
                      <ListItemText
                        primary={session.title}
                        secondary={formatTimeAgo(session.updated_at || session.created_at)}
                        primaryTypographyProps={{ noWrap: true }}
                        secondaryTypographyProps={{ noWrap: true }}
                      />
                      <IconButton
                        size="small"
                        className="delete-session"
                        sx={{ opacity: 0, ".MuiListItemButton-root:hover &": { opacity: 1 } }}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          void onDelete(session.id);
                        }}
                        aria-label="Delete session"
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </ListItemButton>
                  );
                })}
              </Box>
            );
          })}
        </List>
      </Scrollbar>
      <Box sx={{ flexShrink: 0, p: 2, borderTop: 1, borderColor: "divider", display: "flex", alignItems: "center", gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32 }}>
          {(user?.username || "U").slice(0, 1).toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" noWrap>
            {user?.username || "User"}
          </Typography>
          {isOwner ? (
            <Typography component={NextLink} href="/dashboard" variant="caption" color="primary">
              Switch to admin
            </Typography>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}

export { SIDEBAR_WIDTH as WORKSPACE_SIDEBAR_WIDTH };

"use client";

import AddIcon from "@mui/icons-material/Add";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SearchIcon from "@mui/icons-material/Search";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import ChatShellNav from "@/components/chat/ChatShellNav";
import KeprixLogo from "@/components/shared/KeprixLogo";
import { SkeletonText } from "@/components/ui/loading";
import { useStartNewConversation } from "@/hooks/useStartNewConversation";
import { useSessionList } from "@/hooks/useSessionList";
import { groupSessionsByDate, truncateSessionTitle } from "@/lib/session-groups";
import { formatTimeAgo } from "@/lib/time-ago";

type SessionListProps = {
  onNavigate?: () => void;
};

export default function SessionList({ onNavigate }: SessionListProps) {
  const pathname = usePathname();
  const { sessions, remove, isLoading } = useSessionList(100);
  const { startNewConversation, starting } = useStartNewConversation();
  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((session) => (session.title || "").toLowerCase().includes(q));
  }, [query, sessions]);

  const groups = React.useMemo(() => groupSessionsByDate(filtered), [filtered]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <Box sx={{ p: 2, flexShrink: 0, borderBottom: 1, borderColor: "divider" }}>
        <Box component={NextLink} href="/home" sx={{ display: "inline-flex", textDecoration: "none", mb: 1.5 }}>
          <KeprixLogo size="sm" />
        </Box>
        <Box sx={{ display: "grid", gap: 0.75, mb: 1.5 }}>
          <Button component={NextLink} href="/home" size="small" variant="text" sx={{ justifyContent: "flex-start" }}>
            Workspace
          </Button>
          <Button
            component={NextLink}
            href="/files"
            size="small"
            variant="text"
            startIcon={<FolderOutlinedIcon fontSize="small" />}
            sx={{ justifyContent: "flex-start" }}
          >
            Files
          </Button>
        </Box>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<AddIcon />}
          disabled={starting}
          onClick={() => {
            onNavigate?.();
            void startNewConversation();
          }}
        >
          New conversation
        </Button>
        <TextField
          size="small"
          fullWidth
          placeholder="Search sessions"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          sx={{ mt: 1.5 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <List dense disablePadding sx={{ flex: 1, overflow: "auto", px: 1, py: 1 }}>
        {isLoading ? (
          <Box sx={{ px: 2, py: 1, display: "grid", gap: 1.5 }}>
            {Array.from({ length: 5 }).map((_, index) => (
              <SkeletonText key={index} lines={2} />
            ))}
          </Box>
        ) : groups.length === 0 ? (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {query.trim() ? "No conversations match your search." : "No conversations yet."}
            </Typography>
            {!query.trim() ? (
              <Button
                size="small"
                variant="contained"
                onClick={() => {
                  onNavigate?.();
                  void startNewConversation();
                }}
              >
                Start one
              </Button>
            ) : null}
          </Box>
        ) : (
          groups.map((group) => (
            <Box key={group.label} sx={{ mb: 1.5 }}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ px: 1.5, py: 0.5, display: "block", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }}
              >
                {group.label}
              </Typography>
              {group.items.map((session) => {
                const active = pathname === `/chat/${session.id}`;
                return (
                  <ListItemButton
                    key={session.id}
                    component={NextLink}
                    href={`/chat/${session.id}`}
                    selected={active}
                    onClick={onNavigate}
                    sx={{
                      borderRadius: 1,
                      mb: 0.5,
                      borderLeft: active ? 3 : 0,
                      borderColor: "primary.main",
                      pl: active ? 1.25 : 2,
                    }}
                  >
                    <ListItemText
                      primary={truncateSessionTitle(session.title || "Conversation")}
                      secondary={formatTimeAgo(session.updated_at || session.created_at)}
                      primaryTypographyProps={{ noWrap: true }}
                    />
                    <IconButton
                      size="small"
                      edge="end"
                      aria-label="Delete session"
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        if (window.confirm("Delete this conversation?")) {
                          void remove(session.id);
                        }
                      }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </ListItemButton>
                );
              })}
            </Box>
          ))
        )}
      </List>
      <Box sx={{ flexShrink: 0, p: 2, borderTop: 1, borderColor: "divider" }}>
        <ChatShellNav variant="footer" />
      </Box>
    </Box>
  );
}

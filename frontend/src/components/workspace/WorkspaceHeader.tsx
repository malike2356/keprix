"use client";

import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import DownloadIcon from "@mui/icons-material/Download";
import ShareIcon from "@mui/icons-material/Share";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import * as React from "react";
import ModelSelector from "@/components/chat/ModelSelector";
import ChatShellNav from "@/components/chat/ChatShellNav";
import { ceApi } from "@/lib/ce-api";
import { renameConversation } from "@/lib/workspace-api";

type WorkspaceHeaderProps = {
  sessionId?: string;
  title?: string;
};

export default function WorkspaceHeader({ sessionId, title = "New conversation" }: WorkspaceHeaderProps) {
  const [sessionTitle, setSessionTitle] = React.useState(title);
  const [editing, setEditing] = React.useState(false);

  React.useEffect(() => {
    setSessionTitle(title);
  }, [title]);

  const onRename = async () => {
    setEditing(false);
    if (!sessionId || !sessionTitle.trim()) return;
    await renameConversation(sessionId, sessionTitle.trim());
  };

  const onShare = async () => {
    if (!sessionId) return;
    const url = `${window.location.origin}/chat/${sessionId}`;
    await navigator.clipboard.writeText(url);
  };

  const onExport = async (format: "json" | "md") => {
    if (!sessionId) return;
    const response = await ceApi(`/api/workspace/sessions/${sessionId}/export?format=${format}`);
    const blob = await response.blob();
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `session-${sessionId}.${format === "md" ? "md" : "json"}`;
    anchor.click();
    URL.revokeObjectURL(href);
  };

  return (
    <AppBar
      position="static"
      color="transparent"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        backdropFilter: "blur(12px)",
        bgcolor: "background.paper",
      }}
    >
      <Toolbar sx={{ gap: 1.5 }}>
        <ChatShellNav />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {editing ? (
            <TextField
              size="small"
              value={sessionTitle}
              onChange={(event) => setSessionTitle(event.target.value)}
              onBlur={() => void onRename()}
              onKeyDown={(event) => {
                if (event.key === "Enter") void onRename();
              }}
              autoFocus
            />
          ) : (
            <Typography
              variant="subtitle1"
              noWrap
              sx={{ fontWeight: 600, cursor: sessionId ? "text" : "default" }}
              onClick={() => sessionId && setEditing(true)}
            >
              {sessionTitle}
            </Typography>
          )}
        </Box>

        <ModelSelector />

        <Tooltip title="Share session">
          <span>
            <IconButton disabled={!sessionId} onClick={() => void onShare()}>
              <ShareIcon />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title="Export JSON">
          <span>
            <IconButton disabled={!sessionId} onClick={() => void onExport("json")}>
              <DownloadIcon />
            </IconButton>
          </span>
        </Tooltip>
        {sessionId ? (
          <Tooltip title="Open in admin">
            <IconButton component="a" href={`/dashboard/conversations`}>
              <AdminPanelSettingsIcon />
            </IconButton>
          </Tooltip>
        ) : null}
      </Toolbar>
    </AppBar>
  );
}

"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import * as React from "react";
import useSWR from "swr";
import { SkeletonList } from "@/components/ui/loading";
import { fetchBrainSessions, fetchSessionReplay } from "@/lib/brain-replay-api";
import type { SessionReplayData } from "@/types/brain-replay";

type Props = {
  onSelect: (data: SessionReplayData) => void;
  disabled?: boolean;
};

function formatSessionDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function BrainSessionPicker({ onSelect, disabled = false }: Props) {
  const [anchor, setAnchor] = React.useState<HTMLElement | null>(null);
  const [loadingId, setLoadingId] = React.useState<string | null>(null);
  const { data: sessions, isLoading } = useSWR("brain-sessions", fetchBrainSessions);

  const open = Boolean(anchor);

  const handleSelect = async (sessionId: string) => {
    setLoadingId(sessionId);
    try {
      const replay = await fetchSessionReplay(sessionId);
      onSelect(replay);
      setAnchor(null);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <Box>
      <Button
        size="small"
        variant="text"
        disabled={disabled}
        onClick={(event) => setAnchor(event.currentTarget)}
        sx={{ textTransform: "none", color: "text.secondary", minWidth: 0, px: 1, height: 30 }}
      >
        Replay
      </Button>
      <Menu anchorEl={anchor} open={open} onClose={() => setAnchor(null)}>
        {isLoading ? (
          <MenuItem disabled sx={{ display: "block", py: 1.5 }}>
            <SkeletonList rows={3} rowHeight={32} />
          </MenuItem>
        ) : null}
        {(sessions ?? []).map((session) => (
          <MenuItem
            key={session.session_id}
            disabled={loadingId === session.session_id}
            onClick={() => void handleSelect(session.session_id)}
          >
            <ListItemText
              primary={session.title}
              secondary={`${formatSessionDate(session.session_date)} · ${session.activation_count} activations`}
            />
          </MenuItem>
        ))}
        <MenuItem component="a" href="/chat" onClick={() => setAnchor(null)}>
          View all sessions
        </MenuItem>
      </Menu>
    </Box>
  );
}

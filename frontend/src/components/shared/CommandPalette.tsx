"use client";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconSearch } from "@tabler/icons-react";
import Fuse from "fuse.js";
import { useRouter } from "next/navigation";
import * as React from "react";
import useSWR from "swr";
import { ADMIN_NAV_ITEMS } from "@/components/admin/admin-nav";
import { fetchAdminTools } from "@/lib/admin-workspace-api";
import { ceApi } from "@/lib/ce-api";
import { fetchConversations as fetchWorkspaceConversations } from "@/lib/workspace-api";

type PaletteItem = {
  id: string;
  label: string;
  href: string;
  group: string;
  description?: string;
};

type CommandPaletteProps = {
  open: boolean;
  onClose: () => void;
};

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);
  const { data: toolsData } = useSWR(open ? "palette-tools" : null, () => fetchAdminTools());
  const { data: conversations } = useSWR(open ? "palette-conversations" : null, () =>
    fetchWorkspaceConversations(10).catch(() => []),
  );
  const { data: board } = useSWR(open ? "palette-agent-os-board" : null, async () => {
    const response = await ceApi("/api/agent-os/board");
    if (!response.ok) return null;
    return response.json() as Promise<{ config?: { pins?: Array<{ pin_id: string; label: string; id: string; type: string }> } }>;
  });

  const items = React.useMemo(() => {
    const base: PaletteItem[] = [
      {
        id: "workspace-home",
        label: "Workspace home",
        href: "/home",
        group: "Workspace",
        description: "Return to the main workspace start page",
      },
    ];
    for (const entry of ADMIN_NAV_ITEMS.filter((entry) => entry.type === "item")) {
      base.push({
        id: `nav-${entry.href}`,
        label: entry.title,
        href: entry.href,
        group: "Admin pages",
      });
    }
    for (const session of conversations || []) {
      base.push({
        id: `chat-${session.id}`,
        label: session.title,
        href: `/chat/${session.id}`,
        group: "Recent conversations",
        description: session.preview,
      });
    }
    for (const tool of toolsData?.items || []) {
      base.push({
        id: `tool-${tool.id}`,
        label: tool.name,
        href: "/dashboard/tools",
        group: "Tools",
        description: tool.description,
      });
    }
    for (const pin of board?.config?.pins || []) {
      base.unshift({
        id: `run-action-${pin.pin_id}`,
        label: `Run action: ${pin.label}`,
        href: `/agent-os?run=${encodeURIComponent(pin.pin_id)}`,
        group: "Agent OS",
        description: `${pin.type}: ${pin.id}`,
      });
    }
    return base;
  }, [board?.config?.pins, conversations, toolsData?.items]);

  const fuse = React.useMemo(
    () => new Fuse(items, { keys: ["label", "description", "group"], threshold: 0.35 }),
    [items],
  );

  const results = query.trim() ? fuse.search(query).map((result) => result.item) : items.slice(0, 20);

  React.useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const navigate = (href: string) => {
    onClose();
    router.push(href);
  };

  const grouped = React.useMemo(() => {
    const map = new Map<string, PaletteItem[]>();
    for (const item of results) {
      const group = map.get(item.group) || [];
      group.push(item);
      map.set(item.group, group);
    }
    return map;
  }, [results]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { mt: -8 } }}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <Box sx={{ p: 2 }}>
        <TextField
          inputRef={inputRef}
          fullWidth
          placeholder="Search admin pages, conversations, tools..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && results[0]) navigate(results[0].href);
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <IconSearch size={18} stroke={1.75} />
              </InputAdornment>
            ),
          }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Press / to open. Enter to navigate. Esc to close.
        </Typography>
      </Box>
      <List dense sx={{ maxHeight: 360, overflowY: "auto", pb: 1 }}>
        {[...grouped.entries()].map(([group, groupItems]) => (
          <Box key={group}>
            <Typography variant="overline" sx={{ px: 2, color: "text.secondary" }}>
              {group}
            </Typography>
            {groupItems.map((item) => (
              <ListItemButton key={item.id} onClick={() => navigate(item.href)}>
                <ListItemText primary={item.label} secondary={item.description} />
              </ListItemButton>
            ))}
          </Box>
        ))}
        {results.length === 0 ? (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No matching results.
            </Typography>
          </Box>
        ) : null}
      </List>
    </Dialog>
  );
}

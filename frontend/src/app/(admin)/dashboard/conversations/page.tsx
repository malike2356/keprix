"use client";

import { IconExternalLink, IconTrash } from "@tabler/icons-react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import PageContainer from "@/components/shared/PageContainer";
import EmptyState from "@/components/ui/EmptyState";
import { fetchRecentConversations, type ConversationRow } from "@/lib/admin-dashboard-api";
import { deleteConversation } from "@/lib/workspace-api";
import { formatTimeAgo } from "@/lib/time-ago";

function previewText(row: ConversationRow): string {
  const preview = row.preview;
  if (typeof preview === "string") return preview;
  return "";
}

export default function ConversationsPage() {
  const [search, setSearch] = React.useState("");
  const { data, isLoading, mutate } = useSWR("admin-conversations-list", () => fetchRecentConversations(100));

  const rows = (data || []).filter((row) => {
    if (!search.trim()) return true;
    const needle = search.trim().toLowerCase();
    return row.title.toLowerCase().includes(needle) || previewText(row).toLowerCase().includes(needle);
  });

  const onDelete = async (sessionId: string) => {
    await deleteConversation(sessionId);
    await mutate();
  };

  return (
    <PageContainer title="Conversations" description="Review agent conversation sessions across the instance." padded={false}>
      <Box sx={{ display: "grid", gap: 2 }}>
        <TextField
          size="small"
          placeholder="Search by title or preview..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ maxWidth: 360 }}
        />

        <DashboardCard title="Sessions" subtitle={`${rows.length} conversation${rows.length === 1 ? "" : "s"}`}>
          {isLoading ? (
            <LinearProgress />
          ) : rows.length === 0 ? (
            <EmptyState
              title="No conversations yet"
              description="Sessions appear here once users start chatting with the agent."
            />
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Preview</TableCell>
                  <TableCell>Updated</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {row.title}
                      </Typography>
                      <Chip size="small" label={row.id.slice(0, 8)} sx={{ mt: 0.5 }} />
                    </TableCell>
                    <TableCell sx={{ maxWidth: 360 }}>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {previewText(row) || "No messages yet"}
                      </Typography>
                    </TableCell>
                    <TableCell>{formatTimeAgo(row.updated_at || row.created_at)}</TableCell>
                    <TableCell align="right">
                      <Button
                        component="a"
                        href={`/chat/${row.id}`}
                        size="small"
                        startIcon={<IconExternalLink size={16} stroke={1.75} />}
                        sx={{ mr: 1 }}
                      >
                        Open
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        startIcon={<IconTrash size={16} stroke={1.75} />}
                        onClick={() => void onDelete(row.id)}
                      >
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DashboardCard>
      </Box>
    </PageContainer>
  );
}

"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import MemoryIcon from "@mui/icons-material/Memory";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import { ceApi } from "@/lib/ce-api";
import { fetchUiContract } from "@/lib/ui-contract";
import { formatTimeAgo } from "@/lib/time-ago";

type MemoryRow = {
  id: string;
  content: string;
  tags?: string[];
  created_at?: string;
};

async function fetchMemories(): Promise<MemoryRow[]> {
  const response = await ceApi("/api/memory/list");
  if (!response.ok) throw new Error("Failed to load memories");
  const data = (await response.json()) as { memories: MemoryRow[] };
  return data.memories ?? [];
}

async function deleteMemory(id: string): Promise<void> {
  const response = await ceApi(`/api/memory/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Failed to delete memory");
}

export default function MemoryPage() {
  const { data: contract } = useSWR("ui-contract", fetchUiContract);
  const { data: memories, isLoading, mutate } = useSWR("workspace-memory", fetchMemories);
  const empty = contract?.empty_states?.memory;

  const onDelete = async (id: string) => {
    await deleteMemory(id);
    await mutate();
  };

  if (isLoading) {
    return (
      <Box>
        <PageHeader title="Memory" description="Review agent memory and knowledge entries." />
        <SkeletonTable rows={6} columns={4} />
      </Box>
    );
  }

  if (!memories || memories.length === 0) {
    return (
      <Box>
        <PageHeader title="Memory" description="Review agent memory and knowledge entries." />
        <EmptyState
          title={empty?.title ?? "No memory entries"}
          description={empty?.description ?? "Memory will populate as you use chat and research tools."}
          icon={<MemoryIcon sx={{ fontSize: 48 }} />}
        />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader title="Memory" description="Review agent memory and knowledge entries." />
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Content</TableCell>
            <TableCell>Tags</TableCell>
            <TableCell>Created</TableCell>
            <TableCell align="right" />
          </TableRow>
        </TableHead>
        <TableBody>
          {(memories ?? []).map((row) => (
            <TableRow key={row.id}>
              <TableCell sx={{ maxWidth: 480 }}>
                <Typography variant="body2" noWrap>
                  {row.content}
                </Typography>
              </TableCell>
              <TableCell>
                {(row.tags ?? []).map((tag) => (
                  <Chip key={tag} size="small" label={tag} sx={{ mr: 0.5 }} />
                ))}
              </TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  {row.created_at ? formatTimeAgo(row.created_at) : ";"}
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Button size="small" color="error" startIcon={<DeleteOutlineIcon />} onClick={() => onDelete(row.id)}>
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

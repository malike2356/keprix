"use client";

import SearchIcon from "@mui/icons-material/Search";
import TextField from "@mui/material/TextField";
import * as React from "react";
import { ceApi } from "@/lib/ce-api";
import type { BrainNodeKind } from "@/types/brain-graph";

type Match = { id: string; kind: BrainNodeKind; label: string; excerpt: string };

export default function BrainSearchBar({
  query,
  kinds,
  onQuery,
  onResults,
  nodes,
}: {
  query: string;
  kinds: BrainNodeKind[];
  onQuery: (value: string) => void;
  onResults: (matches: Match[]) => void;
  nodes?: Array<{ id: string; kind: BrainNodeKind; label: string; summary: string }>;
}) {
  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!query.trim()) {
        onResults([]);
        return;
      }
      if (nodes) {
        const needle = query.trim().toLowerCase();
        const allowed = new Set(kinds);
        onResults(
          nodes
            .filter((node) => allowed.has(node.kind))
            .filter((node) => node.label.toLowerCase().includes(needle) || node.summary.toLowerCase().includes(needle))
            .slice(0, 50)
            .map((node) => ({
              id: node.id,
              kind: node.kind,
              label: node.label,
              excerpt: node.summary.slice(0, 120),
            })),
        );
        return;
      }
      const params = new URLSearchParams({ q: query, kinds: kinds.join(","), limit: "50" });
      void ceApi(`/api/brain/graph/search?${params.toString()}`)
        .then(async (response) => {
          if (!response.ok) throw new Error("Search failed");
          const payload = (await response.json()) as { matches: Match[] };
          onResults(payload.matches);
        })
        .catch(() => onResults([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [kinds, nodes, onResults, query]);
  return (
    <TextField
      size="small"
      label="Search"
      value={query}
      onChange={(event) => onQuery(event.target.value)}
      InputProps={{ startAdornment: <SearchIcon fontSize="small" sx={{ mr: 0.75, color: "text.secondary" }} /> }}
      sx={{ minWidth: 220 }}
    />
  );
}

"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { alpha } from "@mui/material/styles";
import type { BrainNodeKind, GraphNode } from "@/types/brain-graph";
import { ALL_KINDS } from "@/hooks/useBrainFilters";
import { kindTitle } from "@/components/brain/brain-surface";
import { nodeKindMeta } from "@/components/brain/nodes/node-kinds";
import BrainSearchBar from "@/components/brain/BrainSearchBar";

type Match = { id: string; kind: BrainNodeKind; label: string; excerpt: string };

export default function BrainFilterBar({
  kinds,
  setKinds,
  range,
  setRange,
  sessionId,
  setSessionId,
  query,
  setQuery,
  clear,
  onResults,
  searchNodes,
  showSessionFilters = true,
}: {
  kinds: BrainNodeKind[];
  setKinds: (kinds: BrainNodeKind[]) => void;
  range: string;
  setRange: (range: "all" | "today" | "7d" | "30d") => void;
  sessionId: string;
  setSessionId: (sessionId: string) => void;
  query: string;
  setQuery: (value: string) => void;
  clear: () => void;
  onResults: (matches: Match[]) => void;
  searchNodes?: GraphNode[];
  showSessionFilters?: boolean;
}) {
  const toggleKind = (kind: BrainNodeKind) => {
    setKinds(kinds.includes(kind) ? kinds.filter((item) => item !== kind) : [...kinds, kind]);
  };
  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="center"
      flexWrap="wrap"
      useFlexGap
      sx={{ py: 1, rowGap: 1 }}
    >
      {ALL_KINDS.map((kind) => {
        const active = kinds.includes(kind);
        const meta = nodeKindMeta[kind];
        const Icon = meta.Icon;
        return (
          <Chip
            key={kind}
            size="small"
            icon={<Icon sx={{ fontSize: "16px !important", color: `${meta.color} !important` }} />}
            label={kindTitle(kind)}
            onClick={() => toggleKind(kind)}
            variant={active ? "filled" : "outlined"}
            sx={{
              borderColor: active ? alpha(meta.color, 0.45) : "divider",
              bgcolor: active ? alpha(meta.color, 0.14) : "transparent",
              color: "text.primary",
              fontWeight: active ? 600 : 500,
              "& .MuiChip-label": { px: 0.75 },
            }}
          />
        );
      })}
      <Box sx={{ flex: 1, minWidth: 8 }} />
      {showSessionFilters ? (
        <>
          <TextField
            select
            label="Since"
            size="small"
            value={range}
            onChange={(event) => setRange(event.target.value as "all" | "today" | "7d" | "30d")}
            sx={{ width: 124, "& .MuiOutlinedInput-root": { bgcolor: "transparent" } }}
          >
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="7d">Last 7 days</MenuItem>
            <MenuItem value="30d">Last 30 days</MenuItem>
            <MenuItem value="all">All time</MenuItem>
          </TextField>
          <TextField
            size="small"
            label="Session"
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            sx={{ width: 148, "& .MuiOutlinedInput-root": { bgcolor: "transparent" } }}
          />
        </>
      ) : null}
      <BrainSearchBar query={query} kinds={kinds} onQuery={setQuery} onResults={onResults} nodes={searchNodes} />
      <Button size="small" color="inherit" onClick={clear} sx={{ color: "text.secondary" }}>
        Clear
      </Button>
    </Stack>
  );
}

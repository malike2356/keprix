"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import BrainFilterBar from "@/components/brain/BrainFilterBar";
import BrainGraphCanvas from "@/components/brain/BrainGraphCanvas";
import BrainShareViewHeader from "@/components/brain/BrainShareViewHeader";
import NodeContentPanel from "@/components/brain/NodeContentPanel";
import { nodeKey } from "@/components/brain/graph-transform";
import { useBrainFilters } from "@/hooks/useBrainFilters";
import { fetchSharedBrainData, type SharedBrainData } from "@/lib/brain-share-api";
import type { BrainNodeKind, GraphNode } from "@/types/brain-graph";

function filterSharedGraph(data: SharedBrainData, kinds: BrainNodeKind[], since?: string): SharedBrainData {
  const kindSet = new Set(kinds);
  let nodes = data.nodes.filter((node) => kindSet.has(node.kind));
  if (since) {
    const cutoff = new Date(since).getTime();
    nodes = nodes.filter((node) => new Date(node.created_at).getTime() >= cutoff);
  }
  const allowed = new Set(nodes.map((node) => nodeKey(node.kind, node.id)));
  const edges = data.edges.filter(
    (edge) => allowed.has(nodeKey(edge.source_kind, edge.source_id)) && allowed.has(nodeKey(edge.target_kind, edge.target_id)),
  );
  return {
    ...data,
    nodes,
    edges,
    total_nodes: nodes.length,
    total_edges: edges.length,
    truncated: false,
  };
}

type Props = {
  shareId: string;
};

export default function BrainSharedGraphPage({ shareId }: Props) {
  const [raw, setRaw] = React.useState<SharedBrainData | null>(null);
  const [password, setPassword] = React.useState("");
  const [submittedPassword, setSubmittedPassword] = React.useState<string | null>(null);
  const [needsPassword, setNeedsPassword] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [selected, setSelected] = React.useState<GraphNode | null>(null);
  const [matches, setMatches] = React.useState<Array<{ id: string; kind: BrainNodeKind; label: string; excerpt: string }>>([]);
  const filters = useBrainFilters("shared", { syncUrl: false });
  const highlightedIds = React.useMemo(() => new Set(matches.map((match) => nodeKey(match.kind, match.id))), [matches]);

  const load = React.useCallback(
    async (nextPassword?: string | null) => {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchSharedBrainData(shareId, nextPassword);
        setRaw(payload);
        setNeedsPassword(false);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load shared graph";
        if (message === "password_required") {
          setNeedsPassword(true);
        } else {
          setError(message);
        }
      } finally {
        setLoading(false);
      }
    },
    [shareId],
  );

  React.useEffect(() => {
    void load(submittedPassword);
  }, [load, submittedPassword]);

  const graph = React.useMemo(() => {
    if (!raw) return null;
    return filterSharedGraph(raw, filters.kinds, filters.filters.since);
  }, [filters.filters.since, filters.kinds, raw]);

  if (needsPassword && !raw) {
    return (
      <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 3 }}>
        <Stack spacing={2} sx={{ width: "100%", maxWidth: 420 }}>
          <Typography variant="h6">Password required</Typography>
          <Typography variant="body2" color="text.secondary">
            This shared brain graph is password protected.
          </Typography>
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button
            variant="contained"
            onClick={() => setSubmittedPassword(password)}
          >
            Unlock
          </Button>
        </Stack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 3 }}>
        <Typography variant="h6" color="text.secondary">
          {error === "expired" ? "This share link has expired." : error}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <BrainShareViewHeader title={raw?.title || "Shared brain"} scope={raw?.scope} />
      <BrainFilterBar
        kinds={filters.kinds}
        setKinds={filters.setKinds}
        range={filters.range}
        setRange={filters.setRange}
        sessionId={filters.sessionId}
        setSessionId={filters.setSessionId}
        query={filters.query}
        setQuery={filters.setQuery}
        clear={() => {
          filters.clear();
          setMatches([]);
        }}
        onResults={setMatches}
        searchNodes={raw?.nodes}
        showSessionFilters={false}
      />
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "grid",
          gridTemplateColumns: selected ? "minmax(0, 1fr) 320px" : "minmax(0, 1fr)",
        }}
      >
        <Box sx={{ minWidth: 0, minHeight: 0 }}>
          <BrainGraphCanvas
            filters={filters.filters}
            onNodeSelect={setSelected}
            highlightedIds={highlightedIds}
            readOnly
            staticGraph={graph}
            staticLoading={loading}
          />
        </Box>
        <NodeContentPanel
          node={selected}
          onClose={() => setSelected(null)}
          readOnly
          shareContext={{ shareId, password: submittedPassword }}
          graphData={graph}
        />
      </Box>
      <Box sx={{ borderTop: 1, borderColor: "divider", px: 2, py: 1, textAlign: "center" }}>
        <Typography variant="caption" color="text.secondary">
          Explore with keprix at keprix.app
        </Typography>
      </Box>
    </Box>
  );
}

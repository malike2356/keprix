"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import * as React from "react";
import type { GraphNode } from "@/types/brain-graph";

type Pair = {
  left: GraphNode;
  right: GraphNode;
  similarity: number;
};

type Props = {
  pairs: Pair[];
  onMerge: (keepId: string, deleteId: string) => Promise<void>;
};

export default function DuplicateMerger({ pairs, onMerge }: Props) {
  const [busyKey, setBusyKey] = React.useState<string | null>(null);

  if (pairs.length === 0) {
    return (
      <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Duplicate candidates</Typography>
        <Typography variant="body2" color="text.secondary">No duplicate candidates detected.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1.5, p: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Duplicate candidates</Typography>
      <Stack spacing={1.5}>
        {pairs.map((pair) => {
          const key = `${pair.left.id}:${pair.right.id}`;
          return (
            <Box key={key} sx={{ border: 1, borderColor: "warning.main", borderRadius: 1, p: 1.5 }}>
              <Typography variant="body2">"{pair.left.label}" ~ "{pair.right.label}"</Typography>
              <Typography variant="caption" color="text.secondary">
                Similarity: {pair.similarity}%
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  disabled={busyKey === key}
                  onClick={() => {
                    setBusyKey(key);
                    void onMerge(pair.left.id, pair.right.id).finally(() => setBusyKey(null));
                  }}
                >
                  Keep left
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={busyKey === key}
                  onClick={() => {
                    setBusyKey(key);
                    void onMerge(pair.right.id, pair.left.id).finally(() => setBusyKey(null));
                  }}
                >
                  Keep right
                </Button>
              </Stack>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

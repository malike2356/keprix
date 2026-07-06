"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import * as React from "react";
import { createOpportunity } from "@/lib/opportunity-api";

type Props = {
  onCreated: (opportunityId: string) => void;
};

export default function OpportunityCreatePanel({ onCreated }: Props) {
  const [title, setTitle] = React.useState("");
  const [niche, setNiche] = React.useState("");
  const [goal, setGoal] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleCreate = async () => {
    if (!title.trim()) {
      setError("Title is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const row = await createOpportunity({
        title: title.trim(),
        niche: niche.trim() || undefined,
        goal: goal.trim() || undefined,
      });
      onCreated(row.opportunity_id);
      setTitle("");
      setNiche("");
      setGoal("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
      <Stack spacing={1.5}>
        <TextField
          size="small"
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder='e.g. AI automation for estate agents'
        />
        <TextField
          size="small"
          label="Niche"
          value={niche}
          onChange={(e) => setNiche(e.target.value)}
        />
        <TextField
          size="small"
          label="Goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
        />
        {error ? <Box sx={{ color: "error.main", fontSize: 13 }}>{error}</Box> : null}
        <Button variant="contained" size="small" disabled={busy} onClick={handleCreate}>
          New opportunity
        </Button>
      </Stack>
    </Box>
  );
}

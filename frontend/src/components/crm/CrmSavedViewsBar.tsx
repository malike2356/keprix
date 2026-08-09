"use client";

import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  createCrmSavedView,
  deleteCrmSavedView,
  fetchCrmSavedViews,
  type CrmSavedView,
} from "@/lib/crm-api";
import { CRM_WORKSPACE } from "@/components/crm/types";

type CrmSavedViewsBarProps = {
  workspaceId?: string;
  activeViewId?: string | null;
  onApply: (view: CrmSavedView) => void;
  currentConfig: Record<string, unknown>;
};

export default function CrmSavedViewsBar({
  workspaceId = CRM_WORKSPACE,
  activeViewId,
  onApply,
  currentConfig,
}: CrmSavedViewsBarProps) {
  const [name, setName] = React.useState("");
  const [visibility, setVisibility] = React.useState<"private" | "workspace">("private");
  const [error, setError] = React.useState<string | null>(null);
  const views = useSWR(["crm-saved-views", workspaceId], () => fetchCrmSavedViews(workspaceId));

  const save = async () => {
    if (!name.trim()) return;
    setError(null);
    try {
      await createCrmSavedView(
        { name: name.trim(), visibility, config: currentConfig },
        workspaceId,
      );
      setName("");
      await views.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save view");
    }
  };

  const remove = async (id: string) => {
    setError(null);
    try {
      await deleteCrmSavedView(id, workspaceId);
      await views.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete view");
    }
  };

  const items = views.data?.items ?? [];

  return (
    <Stack spacing={1} sx={{ mb: 1 }}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="body2" color="text.secondary">
          Saved views
        </Typography>
        {items.map((view) => (
          <Chip
            key={view.id}
            label={`${view.name} (${view.visibility})`}
            color={activeViewId === view.id ? "primary" : "default"}
            onClick={() => onApply(view)}
            onDelete={() => void remove(view.id)}
            size="small"
            aria-label={`Apply saved view ${view.name}`}
          />
        ))}
      </Stack>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <TextField
          size="small"
          label="View name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          inputProps={{ "aria-label": "Saved view name" }}
        />
        <Button
          size="small"
          variant={visibility === "private" ? "contained" : "outlined"}
          onClick={() => setVisibility("private")}
        >
          Private
        </Button>
        <Button
          size="small"
          variant={visibility === "workspace" ? "contained" : "outlined"}
          onClick={() => setVisibility("workspace")}
        >
          Workspace
        </Button>
        <Button size="small" variant="outlined" onClick={() => void save()} disabled={!name.trim()}>
          Save view
        </Button>
      </Stack>
      {error ? (
        <Typography variant="caption" color="error">
          {error}
        </Typography>
      ) : null}
    </Stack>
  );
}

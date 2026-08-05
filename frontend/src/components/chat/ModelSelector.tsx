"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { useModelSelector } from "@/hooks/useModelSelector";

type ModelSelectorProps = {
  compact?: boolean;
};

export default function ModelSelector({ compact = false }: ModelSelectorProps) {
  const { models, modelId, active, selectModel, isLoading, error } = useModelSelector();
  const emptyMessage = error
    ? "Models unavailable"
    : isLoading
      ? "Loading models..."
      : "No models configured";

  return (
    <Select
      size="small"
      value={modelId || ""}
      displayEmpty
      disabled={isLoading && models.length === 0}
      onChange={(event) => {
        const next = String(event.target.value);
        if (!next) return;
        selectModel(next);
      }}
      renderValue={() =>
        active ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip size="small" label={active.provider} />
            {!compact ? <Typography variant="body2">{active.name}</Typography> : null}
          </Box>
        ) : (
          emptyMessage
        )
      }
      MenuProps={{
        PaperProps: {
          sx: {
            minWidth: compact ? 180 : 260,
            maxHeight: 360,
          },
        },
      }}
      sx={{ minWidth: compact ? 140 : 220 }}
    >
      {models.length === 0 ? (
        <MenuItem disabled value="" sx={{ minHeight: 40, py: 1 }}>
          {isLoading ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={14} />
              <span>Loading models...</span>
            </Box>
          ) : (
            emptyMessage
          )}
        </MenuItem>
      ) : (
        models.map((item) => (
          <MenuItem key={item.id} value={item.id} sx={{ minHeight: 40, py: 1 }}>
            <Chip size="small" label={item.provider} sx={{ mr: 1 }} />
            {item.name}
          </MenuItem>
        ))
      )}
    </Select>
  );
}

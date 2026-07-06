"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { useModelSelector } from "@/hooks/useModelSelector";

type ModelSelectorProps = {
  compact?: boolean;
};

export default function ModelSelector({ compact = false }: ModelSelectorProps) {
  const { models, modelId, active, selectModel } = useModelSelector();

  return (
    <Select
      size="small"
      value={modelId || ""}
      displayEmpty
      onChange={(event) => selectModel(String(event.target.value))}
      renderValue={() =>
        active ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip size="small" label={active.provider} />
            {!compact ? <Typography variant="body2">{active.name}</Typography> : null}
          </Box>
        ) : (
          "Select model"
        )
      }
      sx={{ minWidth: compact ? 140 : 220 }}
    >
      {models.map((item) => (
        <MenuItem key={item.id} value={item.id}>
          <Chip size="small" label={item.provider} sx={{ mr: 1 }} />
          {item.name}
        </MenuItem>
      ))}
    </Select>
  );
}

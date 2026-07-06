"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";

type ObsidianExportPanelProps = {
  defaultVaultPath?: string;
  loading?: boolean;
  onExport?: (vaultPath: string) => void;
};

export default function ObsidianExportPanel({
  defaultVaultPath = "",
  loading = false,
  onExport,
}: ObsidianExportPanelProps) {
  const [vaultPath, setVaultPath] = React.useState(defaultVaultPath);

  return (
    <Box sx={{ display: "grid", gap: 2, maxWidth: 520 }}>
      <Typography variant="body2" color="text.secondary">
        Export research notes and citations to an Obsidian vault using the same confirmation pattern as file export.
      </Typography>
      <TextField
        label="Vault path"
        value={vaultPath}
        onChange={(event) => setVaultPath(event.target.value)}
        placeholder="/home/user/Obsidian/Research"
        fullWidth
      />
      <Button
        variant="contained"
        disabled={loading || !vaultPath.trim()}
        onClick={() => onExport?.(vaultPath.trim())}
      >
        Export to Obsidian
      </Button>
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { useRouter } from "next/navigation";
import { installIntegration, type ConnectorCatalogItem } from "@/lib/integrations-api";

type Props = {
  item: ConnectorCatalogItem;
  onInstalled: (message: string) => void;
};

export default function InstallButton({ item, onInstalled }: Props) {
  const router = useRouter();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const installed = item.install_status?.installed;

  const onInstall = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await installIntegration(item.connector.id);
      onInstalled(`${item.connector.label} installed`);
      if (result.next_url) {
        router.push(result.next_url);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Button
        variant="contained"
        color={installed ? "success" : "primary"}
        disabled={busy || installed}
        onClick={() => void onInstall()}
        startIcon={busy ? <CircularProgress size={16} color="inherit" /> : undefined}
      >
        {installed ? "Installed" : error ? "Retry install" : "Install"}
      </Button>
      {error ? (
        <Typography variant="caption" color="error" sx={{ display: "block", mt: 0.5 }}>
          {error}
        </Typography>
      ) : null}
    </Box>
  );
}

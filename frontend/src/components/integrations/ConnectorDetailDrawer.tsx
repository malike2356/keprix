"use client";

import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import InstallButton from "@/components/integrations/InstallButton";
import type { ConnectorCatalogItem } from "@/lib/integrations-api";

export default function ConnectorDetailDrawer({
  item,
  onClose,
  onMessage,
}: {
  item: ConnectorCatalogItem | null;
  onClose: () => void;
  onMessage: (message: string) => void;
}) {
  const router = useRouter();
  const connector = item?.connector;

  return (
    <Drawer anchor="right" open={Boolean(item)} onClose={onClose}>
      <Box sx={{ width: { xs: 340, sm: 420 }, p: 3, display: "grid", gap: 2 }}>
        {connector ? (
          <>
            <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 2 }}>
              <Box>
                <Typography variant="h5">{connector.label}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {connector.description}
                </Typography>
              </Box>
              <IconButton onClick={onClose} aria-label="Close">
                <CloseIcon />
              </IconButton>
            </Box>
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
              <Chip label={connector.category} />
              <Chip label={connector.auth_pattern} variant="outlined" />
              <Chip label={connector.scout_audit_class} variant="outlined" />
              {connector.sidecar_id ? <Chip label="Sidecar bridge" color="warning" /> : null}
            </Stack>
            <Typography variant="body2">{connector.install_hint}</Typography>
            <InstallButton item={item} onInstalled={onMessage} />
            <Button
              variant="outlined"
              onClick={() => router.push(`/playbooks/studio/new?connector=${encodeURIComponent(connector.id)}`)}
            >
              Open in Playbook Studio
            </Button>
            {connector.auth_pattern === "mcp" ? (
              <Button component="a" href="/admin/mcp" variant="text">
                Configure MCP
              </Button>
            ) : null}
            {connector.docs_url ? (
              <Button
                component="a"
                href={connector.docs_url}
                variant="text"
                startIcon={<OpenInNewIcon />}
              >
                Documentation
              </Button>
            ) : null}
          </>
        ) : null}
      </Box>
    </Drawer>
  );
}

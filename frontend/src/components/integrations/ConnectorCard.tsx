"use client";

import CircleIcon from "@mui/icons-material/Circle";
import ExtensionIcon from "@mui/icons-material/Extension";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { ConnectorCatalogItem } from "@/lib/integrations-api";

export default function ConnectorCard({
  item,
  onOpen,
}: {
  item: ConnectorCatalogItem;
  onOpen: (item: ConnectorCatalogItem) => void;
}) {
  const { connector, install_status } = item;
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardActionArea onClick={() => onOpen(item)} sx={{ height: "100%" }}>
        <CardContent sx={{ display: "grid", gap: 1.25, height: "100%" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <ExtensionIcon color="primary" />
            <Typography variant="h6" noWrap>
              {connector.label}
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {connector.description}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: "auto" }}>
            <Chip size="small" label={connector.category} />
            <Chip size="small" label={connector.auth_pattern} variant="outlined" />
            <Chip
              size="small"
              icon={<CircleIcon sx={{ fontSize: 10 }} color={install_status.installed ? "success" : "disabled"} />}
              label={install_status.installed ? "Installed" : "Available"}
              variant="outlined"
            />
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

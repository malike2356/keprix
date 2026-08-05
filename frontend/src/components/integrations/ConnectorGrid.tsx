"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ConnectorCard from "@/components/integrations/ConnectorCard";
import type { ConnectorCatalogItem } from "@/lib/integrations-api";

export default function ConnectorGrid({
  items,
  onOpen,
}: {
  items: ConnectorCatalogItem[];
  onOpen: (item: ConnectorCatalogItem) => void;
}) {
  if (!items.length) {
    return (
      <Typography variant="body2" color="text.secondary">
        No integrations match the current filters.
      </Typography>
    );
  }
  return (
    <Box
      sx={{
        display: "grid",
        gap: 2,
        gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
      }}
    >
      {items.map((item) => (
        <ConnectorCard key={item.connector.id} item={item} onOpen={onOpen} />
      ))}
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";

const SERVICES = [
  { name: "Keprix API", status: "operational" },
  { name: "Web UI", status: "operational" },
  { name: "Mutation Engine", status: "operational" },
  { name: "Channel connectors", status: "operational" },
] as const;

export default function StatusPage() {
  return (
    <Container maxWidth="md" sx={{ py: { xs: 8, md: 12 } }}>
      <Typography variant="h3" sx={{ fontWeight: 800, mb: 2 }}>
        Status
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 4, lineHeight: 1.75 }}>
        Self-hosted instances report status locally. This page reflects the default Keprix stack
        components when running on your own infrastructure.
      </Typography>
      <Box sx={{ display: "grid", gap: 2 }}>
        {SERVICES.map((service) => (
          <Box
            key={service.name}
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              p: 2,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography fontWeight={600}>{service.name}</Typography>
            <Chip size="small" color="success" label="Operational" />
          </Box>
        ))}
      </Box>
    </Container>
  );
}

"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

const CONNECTORS = [
  "crm",
  "email",
  "ads",
  "social",
  "website",
  "analytics",
  "stripe",
  "calendar",
  "forms",
];

type Props = {
  integrationsConfig?: Record<string, boolean>;
};

export default function OpportunityIntegrationStatus({ integrationsConfig = {} }: Props) {
  return (
    <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { sm: "repeat(3, 1fr)" } }}>
      {CONNECTORS.map((key) => {
        const connected = Boolean(integrationsConfig[key]);
        return (
          <Box
            key={key}
            sx={{
              px: 1.5,
              py: 1,
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              fontSize: 13,
            }}
          >
            <Typography variant="caption" color="text.secondary" display="block">
              {key}
            </Typography>
            <Typography variant="body2">{connected ? "Connected" : "Not connected"}</Typography>
          </Box>
        );
      })}
    </Box>
  );
}

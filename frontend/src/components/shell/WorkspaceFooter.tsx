"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import DonateCoffeeSheet from "@/components/shell/DonateCoffeeSheet";
import { DEVELOPER_ECOSYSTEM, DEVELOPER_ECOSYSTEM_LABEL } from "@/lib/developer-ecosystem";
import { fetchHealth } from "@/lib/ce-api";

export default function WorkspaceFooter() {
  const [donateOpen, setDonateOpen] = React.useState(false);
  const { data: health } = useSWR("keprix-health-version", fetchHealth, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
  const version = health?.version || "0.16.0";

  return (
    <Box
      component="footer"
      sx={{
        flexShrink: 0,
        py: 1.5,
        px: 2,
        borderTop: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        textAlign: "center",
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block">
        keprix v{version} - Community Edition
        {" · "}
        <Box
          component="button"
          type="button"
          onClick={() => setDonateOpen(true)}
          sx={{
            color: "inherit",
            textDecoration: "none",
            background: "none",
            border: 0,
            padding: 0,
            font: "inherit",
            cursor: "pointer",
            "&:hover": { textDecoration: "underline" },
          }}
        >
          Buy us a coffee
        </Box>
        {" "}
        <Box component="span" sx={{ color: "text.secondary" }}>
          (from £1)
        </Box>
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, fontSize: "0.7rem" }}>
        {DEVELOPER_ECOSYSTEM_LABEL}:{" "}
        {DEVELOPER_ECOSYSTEM.map((item, index) => (
          <Box component="span" key={item.label}>
            {index > 0 ? " · " : null}
            <Box
              component="a"
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              title={item.title}
              sx={{ color: "inherit", textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
            >
              {item.label}
            </Box>
          </Box>
        ))}
      </Typography>
      <DonateCoffeeSheet open={donateOpen} onClose={() => setDonateOpen(false)} />
    </Box>
  );
}

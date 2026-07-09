"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { DEVELOPER_ECOSYSTEM, DEVELOPER_ECOSYSTEM_LABEL } from "@/lib/developer-ecosystem";

export default function WorkspaceFooter() {
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
        keprix - Community Edition
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, fontSize: "0.65rem" }}>
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
    </Box>
  );
}

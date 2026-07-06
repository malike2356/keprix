"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

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
      <Typography variant="caption" color="text.secondary">
        keprix - Community Edition
      </Typography>
    </Box>
  );
}

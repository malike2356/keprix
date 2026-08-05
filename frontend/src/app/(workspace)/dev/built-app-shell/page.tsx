"use client";

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import BuiltAppLayout from "@/components/built-app/BuiltAppLayout";
import type { BuiltAppManifest } from "@/components/built-app/types";

const demoManifest: BuiltAppManifest = {
  id: "demo",
  label: "Demo built app",
  description: "Preview the in-content shell for products built on Keprix.",
  entry: "/dev/built-app-shell",
  version: "0.1.0",
  navigation: {
    style: "sections",
    items: [
      { id: "overview", label: "Overview", href: "/dev/built-app-shell" },
      { id: "finance", label: "Finance", href: "/dev/built-app-shell/finance" },
      { id: "settings", label: "Settings", href: "/dev/built-app-shell/settings" },
    ],
  },
};

export default function BuiltAppShellPreviewPage() {
  return (
    <BuiltAppLayout manifest={demoManifest}>
      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
          <Typography variant="h6">Section workspace</Typography>
          <Typography variant="body2" color="text.secondary">
            This area belongs to the built app while the platform sidebar stays global.
          </Typography>
        </Paper>
        <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" } }}>
          {["Pipeline health", "Queued runs", "Builder notes"].map((label) => (
            <Paper key={label} variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
              <Typography variant="subtitle2">{label}</Typography>
              <Typography variant="h5" sx={{ mt: 1 }}>
                Ready
              </Typography>
            </Paper>
          ))}
        </Box>
      </Stack>
    </BuiltAppLayout>
  );
}

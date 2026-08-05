"use client";

import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export default function BuiltAppDashboardPage() {
  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
        <Typography variant="h6">Dashboard</Typography>
        <Typography variant="body2" color="text.secondary">
          App-owned dashboard content renders inside the Keprix workspace shell.
        </Typography>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
        <Typography variant="subtitle2">Starter status</Typography>
        <Typography variant="h5" sx={{ mt: 1 }}>
          Ready
        </Typography>
      </Paper>
    </Stack>
  );
}

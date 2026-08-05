"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import PageHeader from "@/components/ui/PageHeader";

const escalationTriggers = ["human request", "urgent safety issue", "legal threat", "distressed caller", "two failed attempts"];

export default function ReceptionistSettingsPage() {
  return (
    <Box>
      <PageHeader title="Aiva receptionist" description="Phone persona, booking confirmation, caller memory, and escalation policy." />
      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Default greeting
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Aiva speaking. How can I help?
          </Typography>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Voice behavior
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label="Under 20 seconds" />
            <Chip label="Confirms bookings" />
            <Chip label="Uses caller memory" />
            <Chip label="No billing writes" />
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Escalation
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {escalationTriggers.map((trigger) => (
              <Chip key={trigger} color="warning" variant="outlined" label={trigger} />
            ))}
          </Stack>
        </Paper>
      </Stack>
    </Box>
  );
}

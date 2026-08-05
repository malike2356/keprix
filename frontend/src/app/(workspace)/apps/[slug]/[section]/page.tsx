"use client";

import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useParams } from "next/navigation";

function sectionTitle(section: string): string {
  return section
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function BuiltAppSectionPage() {
  const params = useParams<{ section: string }>();
  const section = Array.isArray(params?.section) ? params.section[0] : params?.section ?? "section";
  const title = sectionTitle(section);

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
        <Typography variant="h6">{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          This placeholder proves built app inner routes switch content without changing the platform shell.
        </Typography>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
        <Typography variant="subtitle2">Route segment</Typography>
        <Typography variant="body1" sx={{ mt: 1 }}>
          /{section}
        </Typography>
      </Paper>
    </Stack>
  );
}

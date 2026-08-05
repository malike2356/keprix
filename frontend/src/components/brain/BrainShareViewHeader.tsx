"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type Props = {
  title?: string;
  scope?: string;
};

export default function BrainShareViewHeader({ title = "Shared brain", scope }: Props) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", px: 2, py: 1.5 }}>
      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" flexWrap="wrap">
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h6">{title}</Typography>
          <Chip size="small" label="Read-only" />
          {scope ? <Chip size="small" variant="outlined" label={scope.replace(/_/g, " ")} /> : null}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Explore with{" "}
          <Link href="https://keprix.app" target="_blank" rel="noreferrer">
            keprix
          </Link>
        </Typography>
      </Stack>
    </Box>
  );
}

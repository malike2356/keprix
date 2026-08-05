"use client";

import BoltIcon from "@mui/icons-material/Bolt";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import type { HubPack } from "@/lib/hub-api";

export default function PersonalOsStarterCard({
  pack,
  onInstall,
}: {
  pack?: HubPack;
  onInstall: (packName: string) => void;
}) {
  return (
    <Card variant="outlined" sx={{ mb: 3, borderColor: "primary.main" }}>
      <CardContent sx={{ display: "grid", gap: 2 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
          <Box>
            <Typography variant="h6">Personal OS Starter</Typography>
            <Typography variant="body2" color="text.secondary">
              Seed skills, a workspace template, audit draft, Agent App stub, and Action Board pins.
            </Typography>
          </Box>
          <Chip size="small" color="primary" label="Free" />
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Button
            variant="contained"
            startIcon={<BoltIcon />}
            disabled={!pack || pack.installed}
            onClick={() => pack && onInstall(pack.name)}
          >
            {pack?.installed ? "Installed" : "Install starter"}
          </Button>
          <Button component={NextLink} href="/agent-os" variant="outlined">
            Open Agent OS
          </Button>
          <Button component={NextLink} href="/agent-os/audit" variant="outlined">
            Review audit
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

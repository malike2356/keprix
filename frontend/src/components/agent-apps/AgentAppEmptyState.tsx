"use client";

import AppsIcon from "@mui/icons-material/Apps";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { useRouter } from "next/navigation";

type Props = {
  onBrowseTemplates?: () => void;
};

export default function AgentAppEmptyState({ onBrowseTemplates }: Props) {
  const router = useRouter();

  return (
    <Box
      sx={{
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 2,
        p: 4,
        textAlign: "center",
      }}
    >
      <AppsIcon sx={{ fontSize: 40, color: "text.secondary", mb: 1 }} />
      <Typography variant="h6" gutterBottom>
        Install your first agent app
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 480, mx: "auto" }}>
        Browse ready-made templates for standups, research briefs, and more. Install in one click and run from the web UI.
      </Typography>
      <Box sx={{ display: "flex", gap: 1, justifyContent: "center", flexWrap: "wrap" }}>
        <Button variant="contained" onClick={onBrowseTemplates}>
          Browse templates
        </Button>
        <Button variant="outlined" onClick={() => router.push("/agent-apps/install")}>
          Upload app bundle
        </Button>
      </Box>
    </Box>
  );
}

"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import PageHeader from "@/components/ui/PageHeader";
import type { BuiltAppManifest, BuiltAppNavItem } from "@/components/built-app/types";

type BuiltAppHeaderProps = {
  manifest: BuiltAppManifest;
  activeItem: BuiltAppNavItem | null;
  actions?: React.ReactNode;
};

export default function BuiltAppHeader({ manifest, activeItem, actions }: BuiltAppHeaderProps) {
  return (
    <PageHeader
      title={manifest.label}
      description={manifest.description}
      breadcrumbs={[
        { label: "Workspace home", href: "/home" },
        { label: manifest.label, href: manifest.entry },
        { label: activeItem?.label ?? "Overview" },
      ]}
      actions={
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          {manifest.version ? (
            <Chip
              size="small"
              label={`v${manifest.version}`}
              sx={{
                borderColor: manifest.brand?.primary_color,
                color: manifest.brand?.primary_color,
              }}
              variant="outlined"
            />
          ) : null}
          {actions}
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button component="a" href="/home" size="small" variant="outlined">
              Back to workspace
            </Button>
            <Button component="a" href="/agent-apps" size="small" variant="text">
              All apps
            </Button>
          </Box>
        </Stack>
      }
    />
  );
}

"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import { useParams } from "next/navigation";
import BuiltAppLayout from "@/components/built-app/BuiltAppLayout";
import { SkeletonList } from "@/components/ui/loading";
import { useBuiltAppManifest } from "@/hooks/useBuiltAppManifest";

export default function BuiltAppRouteLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ slug: string }>();
  const slug = Array.isArray(params?.slug) ? params.slug[0] : params?.slug ?? "";
  const { manifest, error, isLoading } = useBuiltAppManifest(slug);

  if (isLoading) {
    return <SkeletonList rows={4} rowHeight={56} />;
  }

  if (error || !manifest) {
    return (
      <Stack spacing={2}>
        <Alert severity="error">{error instanceof Error ? error.message : "Built app not found"}</Alert>
        <Box>
          <Button component="a" href="/home" variant="outlined">
            Back to workspace
          </Button>
        </Box>
      </Stack>
    );
  }

  return <BuiltAppLayout manifest={manifest}>{children}</BuiltAppLayout>;
}
